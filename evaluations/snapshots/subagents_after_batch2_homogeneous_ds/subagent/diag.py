import json
from tools import execute_shell_command
from llm import call_llm


def main(query: str) -> dict:
    # General diagnostic: inspect files and directory structure described in the query.
    ls = execute_shell_command('ls -la . && echo "---CHARTS---" && ls -la charts 2>/dev/null')
    # Try to locate fit stats and scatter data files
    found = {}
    for path in ['fit_stats.json', 'charts/fit_stats.json', 'scatter_data.json', 'charts/scatter_data.json', 'wb_multi_data.json']:
        out = execute_shell_command('cat ' + path + ' 2>/dev/null')
        if out and out.strip() and 'No such file' not in out and 'cannot' not in out.lower():
            found[path] = out.strip()[:2000]
    report = 'DIRECTORY:\n' + ls + '\n\nFILES FOUND:\n' + json.dumps(found, indent=2, ensure_ascii=False)
    summary = call_llm(
        system='You are a file-system diagnostician. Summarize what files exist and report the exact contents of fit statistics and scatter data files.',
        messages=[{'role': 'user', 'content': 'Diagnostic request: ' + query + '\n\nObserved:\n' + report + '\n\nReport findings factually.'}],
        max_tokens=1500,
    )
    return {'answer': report[:4000], 'summary': summary}
