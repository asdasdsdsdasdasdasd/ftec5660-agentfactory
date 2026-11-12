import json
from llm import call_llm
from tools import execute_shell_command


def main(query: str) -> dict:
    evidence = []

    # 1. Locate the file
    ls = execute_shell_command("ls -la *.py 2>&1")
    evidence.append("LS:\n" + ls)

    # 2. Show the file content with line numbers (head + tail)
    head = execute_shell_command("head -n 150 solution.py 2>&1")
    evidence.append("HEAD 150:\n" + head)
    total = execute_shell_command("wc -l solution.py 2>&1")
    evidence.append("WC:\n" + total)

    # 3. Look for key required components via grep
    greps = {}
    for kw in ["class ", "tkinter", "def main", "score", "clear", "rotation", "__main__", "bind", "def rotate", "pause", "lines"]:
        out = execute_shell_command(f"grep -n '{kw}' solution.py 2>&1 | head -8")
        greps[kw] = out
    evidence.append("GREPS:\n" + json.dumps(greps, indent=1)[:2000])

    # 4. Try a real import test of the module (protected so GUI won't launch)
    import_test = execute_shell_command(
        "python - <<'PY' 2>&1 | tail -40\n"
        "import importlib.util, ast\n"
        "src=open('solution.py').read()\n"
        "tree=ast.parse(src)\n"
        "names=[n.name for n in ast.walk(tree) if isinstance(n,(ast.ClassDef,ast.FunctionDef))]\n"
        "print('TOPLEVEL_DEFS:', names)\n"
        "# count imports\n"
        "imps=[]\n"
        "for n in ast.walk(tree):\n"
        "    if isinstance(n,ast.Import):\n"
        "        imps+=[a.name for a in n.names]\n"
        "    if isinstance(n,ast.ImportFrom):\n"
        "        imps.append(n.module)\n"
        "print('IMPORTS:', imps)\n"
        "PY"
    )
    evidence.append("STRUCTURE:\n" + import_test)

    # 5. Try running with a non-interactive safety: set a timeout, headless
    run_test = execute_shell_command(
        "timeout 5 python solution.py < /dev/null 2>&1 | head -30; echo EXIT_CODE:$?"
    )
    evidence.append("RUN TEST (5s timeout, no stdin):\n" + run_test)

    summary = call_llm(
        system="You are a code reviewer. Based on the evidence, assess whether the Python program is complete, correctly structured, and addresses the task requirements. Report concrete findings, bugs, or missing pieces.",
        messages=[{"role": "user", "content": f"Task: {query}\n\nEvidence:\n" + "\n\n".join(evidence) + "\n\nAssess: Is the code present and complete? Are the required features (keyboard controls, scoring, line clearing, game loop, GUI) implemented? Any obvious bugs? Report findings."}],
        max_tokens=2000,
    )

    answer = execute_shell_command("wc -l solution.py 2>&1 && head -20 solution.py 2>&1")
    return {"answer": answer[:1500], "summary": summary}
