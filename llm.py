import os
import json
import time
from typing import List, Dict
from openai import OpenAI
import requests

USAGE = {
    "meta": {"completion_tokens": 0, "prompt_tokens": 0, "calls": 0},
    "subagent": {"completion_tokens": 0, "prompt_tokens": 0, "calls": 0},
}


def reset_usage():
    for role in USAGE:
        USAGE[role] = {"completion_tokens": 0, "prompt_tokens": 0, "calls": 0}


def snapshot_usage():
    return json.loads(json.dumps(USAGE))


def _role_for_current_config() -> str:
    role = os.environ.get("LLM_ROLE", "").strip()
    if role in ("meta", "subagent"):
        return role
    model = os.environ.get("LLM_MODEL", "")
    sub_model = os.environ.get("SUBAGENT_MODEL", "")
    if sub_model and model == sub_model:
        return "subagent"
    return "meta"


def _record_usage(usage) -> None:
    if usage is None:
        return
    role = _role_for_current_config()
    USAGE[role]["calls"] += 1
    USAGE[role]["completion_tokens"] += int(getattr(usage, "completion_tokens", 0) or 0)
    USAGE[role]["prompt_tokens"] += int(getattr(usage, "prompt_tokens", 0) or 0)


def _get_config():
    """Read LLM config from environment variables at call time."""
    return {
        "url": os.environ.get("LLM_URL", ""),
        "api_key": os.environ.get("LLM_API_KEY", ""),
        "model": os.environ.get("LLM_MODEL", ""),
        "protocol": os.environ.get("LLM_PROTOCOL", "OPENAI_STYLE"),
    }


def call_llm_anthropic(
    system: str,
    messages: List[Dict[str, str]],
    max_tokens: int = 8000,
    max_retries: int = 5
) -> str:
    """Call the LLM API using streaming to avoid proxy timeout."""
    cfg = _get_config()
    headers = {
        "Content-Type": "application/json",
        "x-api-key": cfg["api_key"],
        "anthropic-version": "2023-06-01"
    }
    data = {
        "model": cfg["model"],
        "max_tokens": max_tokens,
        "system": [{"type": "text", "text": system}],
        "messages": messages,
        "stream": True
    }
    for attempt in range(max_retries):
        try:
            response = requests.post(
                cfg["url"] + "/messages",
                headers=headers,
                json=data,
                timeout=60,
                stream=True
            )
            response.raise_for_status()
            response.encoding = "utf-8"

            full_text = ""
            for line in response.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                payload = line[len("data: "):]
                if payload.strip() == "[DONE]":
                    break
                try:
                    event = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                event_type = event.get("type", "")
                if event_type == "content_block_delta":
                    delta = event.get("delta", {})
                    if delta.get("type") == "text_delta":
                        full_text += delta.get("text", "")
                elif event_type == "message_stop":
                    break

            if full_text:
                return full_text
            else:
                raise Exception("Empty response from streaming API")
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                wait = min(wait, 60)
                print(f"[LLM] Attempt {attempt + 1} failed: {e}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                return f"Error: {str(e)}"

def call_llm_openai(
    system: str,
    messages: List[Dict[str, str]],
    max_tokens: int = 8000,
    max_retries: int = 5,
    temperature: float = 1.0,
    top_p: float = 0.95
) -> str:
    cfg = _get_config()
    timeout = 600.0 if "127.0.0.1" in (cfg["url"] or "") or "localhost" in (cfg["url"] or "") else 180.0
    client = OpenAI(api_key=cfg["api_key"] or "none", base_url=cfg["url"], timeout=timeout)
    all_messages = []
    if system:
        all_messages.append({"role": "system", "content": system})
    all_messages.extend(messages)

    requested = min(int(max_tokens or 8000), 8192)
    create_kwargs = {
        "model": cfg["model"],
        "max_tokens": requested,
        "temperature": temperature,
        "top_p": top_p,
        "messages": all_messages,
    }
    local = "127.0.0.1" in (cfg["url"] or "") or "localhost" in (cfg["url"] or "")
    # Thinking consumes the whole max_tokens budget on local Qwen (subagents often
    # pass 500-800), which yields empty content and a multi-minute retry storm.
    if "deepseek.com" in (cfg["url"] or ""):
        create_kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
    elif local:
        create_kwargs["extra_body"] = {
            "chat_template_kwargs": {"enable_thinking": False, "reasoning_effort": "low"},
        }

    retries = min(int(max_retries or 5), 8)
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(**create_kwargs)
            _record_usage(getattr(response, "usage", None))
            msg = response.choices[0].message
            text = (msg.content or "").strip()
            if not text:
                text = (getattr(msg, "reasoning_content", None) or "").strip()
            if not text:
                # Do not exponential-backoff empty local replies: they will stay empty.
                if local:
                    return ""
                raise Exception("Empty content from chat.completions")
            return text
        except Exception as e:
            if attempt < retries - 1:
                wait = 2 ** attempt
                wait = min(wait, 8 if local else 60)
                print(f"[LLM] Attempt {attempt + 1} failed: {e}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                return f"Error: {str(e)}"

def call_llm(
    system: str,
    messages: List[Dict[str, str]],
    max_tokens: int = 8000,
    max_retries: int = 8
) -> str:
    cfg = _get_config()
    if cfg["protocol"] == "OPENAI_STYLE":
        return call_llm_openai(system, messages, max_tokens, max_retries)
    elif cfg["protocol"] == "ANTHROPIC_STYLE":
        return call_llm_anthropic(system, messages, max_tokens, max_retries)
    else:
        raise ValueError(f"Unsupported protocol: {cfg['protocol']}")
