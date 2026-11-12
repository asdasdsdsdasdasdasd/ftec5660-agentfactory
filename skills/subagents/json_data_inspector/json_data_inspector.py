import json
import os
import re
from llm import call_llm
from tools import execute_shell_command


def main(query: str) -> dict:
    # Extract filename from query via LLM
    plan = call_llm(
        system="Extract the JSON filename to inspect from the query. Return ONLY the filename string, nothing else.",
        messages=[{'role': 'user', 'content': query}],
        max_tokens=100,
    )
    fname = (plan or '').strip().strip('"\'').split()[0] if plan else 'fetched_data.json'
    if not os.path.exists(fname):
        return {'answer': 'File not found: ' + fname, 'summary': 'The specified JSON file does not exist in the workspace. Files present: ' + execute_shell_command('ls *.json 2>&1')[:500]}
    snippet = execute_shell_command('python -c "import json; d=json.load(open(\'%s\')); print(json.dumps(d.get(\'metrics\'), indent=2)); r=d.get(\'rows\',[]); print(\'NROWS\', len(r)); print(json.dumps(r[:3], indent=2)); print(json.dumps(r[-2:], indent=2))" 2>&1' % fname)
    # Also count non-null values per metric key
    count_script = 'python -c "import json; d=json.load(open(\'%s\')); r=d.get(\'rows\',[]); keys=set(); [keys.update(x.keys()) for x in r]; print(\'KEYS\', sorted(keys));\nimport collections\nfor k in keys:\n    if k in (\'country\',\'year\'): continue\n    c=sum(1 for x in r if isinstance(x.get(k),(int,float)) and x.get(k)==x.get(k))\n    print(k, c, \'nonnull of\', len(r))"' % fname
    counts = execute_shell_command(count_script)
    summary = call_llm(
        system='You are a data inspector. Summarize what data the JSON file contains, how many non-null values each metric has, and whether the data looks complete/usable.',
        messages=[{'role': 'user', 'content': 'Query: ' + query + '\n\nSnippet:\n' + snippet + '\n\nCounts:\n' + counts}],
        max_tokens=800,
    )
    return {'answer': 'Inspected ' + fname + '. Snippet:\n' + snippet[:1500] + '\n\nCounts:\n' + counts[:800], 'summary': summary}
