from llm import call_llm
from tools import execute_shell_command
import json, re


def main(query: str) -> dict:
    # LLM generates read-only diagnostic shell commands for the goal
    plan = call_llm(
        system="You are a shell diagnostics expert. Given a goal, output ONLY a JSON array of safe read-only bash commands (no rm/mv/destructive) that gather the needed evidence. Include commands to check xvfb, DISPLAY, audio devices, playwright browsers, package presence, etc., as relevant to the goal.",
        messages=[{"role": "user", "content": f"Goal: {query}\n\nReturn ONLY a JSON array of command strings, max 20."}],
        max_tokens=1200,
    )
    cmds = []
    try:
        m = re.search(r'\[.*\]', plan, re.DOTALL)
        if m:
            cmds = json.loads(m.group(0))
    except Exception as e:
        return {"answer": "parse error", "summary": f"Could not parse commands from LLM: {e}\nRaw: {plan}"}
    outputs = {}
    for c in cmds:
        try:
            outputs[c] = execute_shell_command(c)[:1500]
        except Exception as e:
            outputs[c] = f"ERROR: {e}"
    summary = call_llm(
        system="Summarize the diagnostic command outputs and answer the goal concretely.",
        messages=[{"role": "user", "content": f"Goal: {query}\n\nOutputs:\n" + json.dumps(outputs, ensure_ascii=False)[:5000] + "\n\nWrite a SUMMARY (100-1000 words)."}],
        max_tokens=1500,
    )
    return {"answer": json.dumps(outputs, ensure_ascii=False)[:4000], "summary": summary}
