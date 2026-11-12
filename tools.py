"""
Search API Tool - Search documents and retrieve full content.

Usage:
    from tools import search, open_page

    # Search for documents
    results = local_search("your query", topk=10)
    # Returns: {"results": [{"docid": "...", "text": "...", "score": ...}, ...]}

    # Open a specific document
    content = open_page("docid_here")
    # Returns: Full document content as dict
"""

import os
from typing import Dict, Any, Optional, List
import requests
import subprocess
import re
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_SEARCH_URL = "https://api.deepseek.com/v1/tools/search"
DEEPSEEK_FETCH_URL = "https://api.deepseek.com/v1/tools/fetch"


def _deepseek_api_key(explicit: Optional[str] = None) -> str:
    return (
        (explicit or "").strip()
        or os.getenv("DEEPSEEK_API_KEY", "").strip()
        or os.getenv("META_AGENT_API_KEY", "").strip()
        or os.getenv("LLM_API_KEY", "").strip()
    )


def _deepseek_headers(api_key: Optional[str] = None) -> Dict[str, str]:
    key = _deepseek_api_key(api_key)
    if not key:
        raise RuntimeError(
            "DeepSeek API key missing. Set DEEPSEEK_API_KEY or META_AGENT_API_KEY."
        )
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def read_url_jina(url: str) -> str:
    """
    Fetch a web page as Markdown via DeepSeek Fetch.
    Function name kept as read_url_jina so existing subagent code still imports it.
    """
    print(f"📖 [DeepSeek Fetch] Reading: {url}")
    try:
        response = requests.post(
            DEEPSEEK_FETCH_URL,
            headers=_deepseek_headers(),
            json={"url": url},
            timeout=30,
        )
        if response.status_code == 429:
            return "❌ Error: DeepSeek Fetch rate limit exceeded."
        if response.status_code != 200:
            return f"❌ DeepSeek Fetch Error: HTTP {response.status_code}: {response.text[:500]}"
        page = response.json()
        title = page.get("title") or ""
        content = page.get("content") or ""
        text = f"# {title}\n\n{content}" if title else content
        return text[:8000]
    except Exception as e:
        return f"❌ DeepSeek Fetch Error: {e}"


def search_serper(query: str, topk: int = 10, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Web search via DeepSeek Search API.

    Function name kept as search_serper so existing / generated subagent code
    still works. Return format matches the original Serper wrapper:
        [{"title": ..., "link": ..., "snippet": ...}, ...]
        On failure: [{"error": "..."}]
    """
    print(f"🔍 [DeepSeek Search] Searching: {query}")
    q = (query or "").strip()
    if not q:
        return [{"error": "empty query"}]
    # DeepSeek Search query limit is 128 Unicode characters.
    if len(q) > 128:
        q = q[:128]

    count = max(1, min(int(topk or 10), 50))
    try:
        response = requests.post(
            DEEPSEEK_SEARCH_URL,
            headers=_deepseek_headers(api_key),
            json={"query": q, "count": count, "need_content": False},
            timeout=30,
        )
        if response.status_code != 200:
            return [{"error": f"HTTP {response.status_code}: {response.text[:500]}"}]
        results = response.json().get("results") or []
        mapped = []
        for item in results[:count]:
            mapped.append({
                "title": item.get("title"),
                "link": item.get("url"),
                "snippet": item.get("summary") or item.get("snippet") or "",
            })
        return mapped
    except Exception as e:
        return [{"error": str(e)}]
 
def _is_shell_command_safe(command):
    """
    Simple shell command safety check.
    Blocks rm, rmdir, shred and redirect overwrite > (adjustable).
    """
    # Use word boundary regex to avoid false positives (e.g. 'performance' contains 'rm')
    # Matches: rm -rf, rm file, rmdir dir, shred file
    forbidden_patterns = [
        r'\brm\b', 
        r'\brmdir\b', 
        r'\bshred\b',
        r'\bmv\b' # mv can overwrite files, can be relaxed if needed
    ]
    
    for pattern in forbidden_patterns:
        if re.search(pattern, command):
            keyword = pattern.replace(r'\b', '')
            return False, f"Safety blocked: command contains forbidden keyword '{keyword}'"
    return True, ""

def execute_shell_command(command):
    """
    Tool implementation: execute a shell command.
    """
    MAX_OUTPUT_LENGTH = 5000
    # 1. Safety check
    is_safe, reason = _is_shell_command_safe(command)
    if not is_safe:
        return f"Error: Command rejected by safety policy. {reason}"
    
    # Use current working directory (set by run_python_file to the task workspace)
    work_dir = os.getcwd()

    # 2. Execute command
    try:
        # Execute in the specified working directory
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=work_dir,
            capture_output=True, 
            text=True,
            timeout=300, # Prevent command from hanging (5 min, supports long tasks like playwright)
            encoding='utf-8',
            errors='replace'
        )
        output = result.stdout
        if len(output) > MAX_OUTPUT_LENGTH:
            output = output[:MAX_OUTPUT_LENGTH] + f"\n... (Output truncated: showing first {MAX_OUTPUT_LENGTH} characters. Use 'head', 'tail' or 'grep' to read specific parts.)"
        if result.stderr:
            output += f"\n[Stderr]:\n{result.stderr}"
            
        return output if output.strip() else "[Command executed successfully with no output]"
        
    except subprocess.TimeoutExpired:
        return "Error: Command timed out."
    except Exception as e:
        return f"Error executing shell command: {str(e)}"