import json
import re
from llm import call_llm
from tools import execute_shell_command

MAX_ITER = 4


def _extract_code(text):
    blocks = re.findall(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    if blocks:
        return max(blocks, key=len).strip()
    return text.strip()


def _validate_syntax(code):
    fname = "_syntax_check.py"
    with open(fname, "w") as f:
        f.write(code)
    return execute_shell_command(f"python -m py_compile {fname} 2>&1 && echo SYNTAX_OK")


def main(query: str) -> dict:
    evidence = []
    final_code = None
    code = None
    final_status = ""

    plan = call_llm(
        system="You are a senior software engineer. Analyze a programming task and plan a clean, complete, runnable implementation. Prefer the standard library.",
        messages=[{"role": "user", "content": f"Task: {query}\n\nWrite a concise implementation plan: required features, chosen library/libraries, key components."}],
        max_tokens=1500,
    )
    evidence.append("PLAN:\n" + plan)

    env_check = execute_shell_command(
        "python -c 'import tkinter; print(\"tkinter:OK\")' 2>&1 | head -1; python --version 2>&1"
    )
    evidence.append("ENV CHECK:\n" + env_check)

    feedback = ""
    for iteration in range(MAX_ITER):
        gen_prompt = f"Task: {query}\n\nImplementation plan:\n{plan}\n\nEnvironment:\n{env_check}\n\n"
        if feedback:
            gen_prompt += f"Previous attempt had issues, fix them:\n{feedback}\n\n"
        gen_prompt += (
            "Write a COMPLETE, self-contained, runnable Python program that fully solves the task. "
            "Use the standard library only unless a third-party library is confirmed available. "
            "If tkinter is available, prefer it for GUI games. "
            "The program must define an entry point and launch (e.g., if __name__ == '__main__': ...). "
            "Return ONLY the code inside a single fenced python code block with no extra commentary."
        )
        code_resp = call_llm(
            system="You are an expert Python programmer. Output only valid, complete, runnable Python code in a single fenced python code block.",
            messages=[{"role": "user", "content": gen_prompt}],
            max_tokens=6000,
        )
        if code_resp.startswith("Error:"):
            feedback = "LLM generation failed, try again."
            continue
        code = _extract_code(code_resp)

        check = _validate_syntax(code)
        evidence.append(f"Iteration {iteration+1} syntax check: " + check[:300])
        if "SYNTAX_OK" not in check:
            feedback = "Syntax error:\n" + check
            continue

        ast_check = execute_shell_command(
            "python -c \"import ast; src=open('_syntax_check.py').read(); ast.parse(src); print('AST_OK')\" 2>&1 | tail -5"
        )
        evidence.append(f"Iteration {iteration+1} AST check: " + ast_check[:300])
        if "AST_OK" not in ast_check:
            feedback = "AST parse failed:\n" + ast_check
            continue

        final_code = code
        final_status = "validated (syntax + AST pass)"
        break

    if final_code is None:
        final_code = code if code else "# generation failed"
        final_status = "best-effort (validation did not fully pass)"

    out_path = "solution.py"
    with open(out_path, "w") as f:
        f.write(final_code)

    summary = call_llm(
        system="You are a technical writer summarizing a code-generation session. Be concise but include evidence.",
        messages=[{"role": "user", "content": f"Task: {query}\n\nEvidence:\n" + "\n\n".join(evidence[:12]) + f"\n\nFinal status: {final_status}\nFile saved: {out_path}\n\nWrite a SUMMARY (100-2000 words) describing the approach, libraries used, validation performed, and outcome."}],
        max_tokens=2000,
    )

    answer = f"Generated a Python program for the task and saved it to '{out_path}'. Status: {final_status}."
    return {"answer": answer, "summary": summary}
