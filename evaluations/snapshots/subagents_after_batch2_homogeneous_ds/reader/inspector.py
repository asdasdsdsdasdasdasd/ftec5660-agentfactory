import json
import os
from llm import call_llm
from tools import execute_shell_command


def main(query: str) -> dict:
    """Inspect files in the workspace. The query should describe which file(s)
    or glob pattern to inspect. Reports structure/size samples so the caller can
    diagnose data issues. Generic utility.
    """
    plan = call_llm(
        system="You are a file inspection planner. Given a request, return JSON with key 'patterns' (list of shell glob/filenames to inspect) and 'goal' (what to report). Return ONLY valid JSON.",
        messages=[{"role": "user", "content": f"Request: {query}"}],
        max_tokens=400,
    )
    import re
    try:
        plan_json = json.loads(re.search(r"\{.*\}", plan, re.DOTALL).group(0))
    except Exception:
        plan_json = {"patterns": ["*"], "goal": query}

    report = []
    for pat in plan_json.get("patterns", ["*"]):
        ls = execute_shell_command(f"ls -la {pat} 2>&1 | head -30")
        report.append(f"=== ls {pat} ===\n{ls}")

    # If a json file exists, dump its top-level structure
    jsons = execute_shell_command("ls *.json 2>/dev/null")
    for fn in jsons.split():
        head = execute_shell_command(f"head -c 4000 {fn} 2>&1")
        report.append(f"=== head of {fn} ===\n{head}")
        try:
            with open(fn) as f:
                data = json.load(f)
            if isinstance(data, dict):
                struct = {k: (len(v) if isinstance(v, (list, dict, str)) else v) for k, v in data.items()}
                report.append(f"=== structure of {fn} ===\n{json.dumps(struct, default=str)[:2000]}")
                if "evidence" in data:
                    report.append(f"evidence type={type(data['evidence']).__name__}, len={len(data['evidence']) if hasattr(data['evidence'],'__len__') else 'NA'}")
        except Exception as e:
            report.append(f"could not parse {fn}: {e}")

    combined = "\n".join(report)[:8000]
    analysis = call_llm(
        system="You are a diagnostic assistant. Summarize what files exist and report any data structure problems (e.g. empty arrays, truncated JSON, wrong types).",
        messages=[{"role": "user", "content": combined}],
        max_tokens=1000,
    )

    return {"answer": analysis, "summary": combined}
