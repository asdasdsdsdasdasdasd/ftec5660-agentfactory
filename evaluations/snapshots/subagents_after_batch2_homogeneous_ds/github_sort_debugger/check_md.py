from tools import execute_shell_command
from llm import call_llm


def main(query: str) -> dict:
    out = execute_shell_command("ls -la *.md 2>&1; echo '---CONTENT---'; cat meta_ai_github_org.md 2>&1 | head -n 150")
    summary = call_llm(
        system="Report whether the markdown file exists and summarize its contents faithfully.",
        messages=[{"role": "user", "content": out}],
        max_tokens=1500,
    )
    return {"answer": out[:3000], "summary": summary}
