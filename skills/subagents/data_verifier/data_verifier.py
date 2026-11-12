import json
import os
from llm import call_llm
from tools import execute_shell_command


def main(query: str) -> dict:
    ls = execute_shell_command('ls -1 *.json 2>/dev/null')
    files = [x.strip() for x in ls.splitlines() if x.strip()]
    logic = ["Found JSON files: " + str(files)]

    contents = {}
    for fn in files:
        try:
            with open(fn, 'r', encoding='utf-8', errors='replace') as f:
                contents[fn] = json.load(f)
        except Exception as e:
            contents[fn] = {"error": str(e)}

    pick = call_llm(
        system=("You are a data file inspector. Given a request and a list of JSON file names with small previews, return ONLY the filename that best matches the request, or ALL if unclear. Return just the filename, nothing else."),
        messages=[{"role": "user", "content": "Request: " + query + "\nFiles:\n" + json.dumps({k: str(v)[:300] for k, v in contents.items()})}],
        max_tokens=100,
    ).strip().strip('"').strip("'")

    if pick in contents:
        selected = {pick: contents[pick]}
    else:
        selected = contents

    full = json.dumps(selected, indent=2, ensure_ascii=False)
    answer = full[:4500]

    summary = call_llm(
        system="You are a data verification summarizer. Describe what data was found in the file(s), including structure and key values.",
        messages=[{"role": "user", "content": "Request: " + query + "\nLog:\n" + "\n".join(logic) + "\nData:\n" + full[:4000] + "\n\nWrite a concise but complete SUMMARY."}],
        max_tokens=1500,
    )
    return {"answer": answer, "summary": summary}
