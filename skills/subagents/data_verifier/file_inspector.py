import json
from llm import call_llm
from tools import execute_shell_command


def main(query: str) -> dict:
    # LLM turns the inspection request into safe read-only shell commands.
    plan = call_llm(
        system=(
            "You are a file inspector. Given a request to inspect files, return ONLY a single "
            "shell command (read-only, no rm/mv) that lists files and prints relevant JSON/text "
            "contents (use ls, cat, head, stat, wc). Keep it to one line. Return only the command."
        ),
        messages=[{"role": "user", "content": "Inspection request: " + query}],
        max_tokens=300,
    ).strip().strip('`').strip()
    if plan.startswith('sh') or plan.startswith('bash'):
        plan = plan.split('\n', 1)[-1].strip()
    out = execute_shell_command(plan)
    logic = "Command: " + plan + "\nOutput:\n" + str(out)[:4000]
    summary = call_llm(
        system="You are a file inspection summarizer. Report exactly what was found: file existence, sizes, and contents.",
        messages=[{"role": "user", "content": logic + "\n\nWrite a factual SUMMARY."}],
        max_tokens=1000,
    )
    return {"answer": str(out)[:4500], "summary": summary}
