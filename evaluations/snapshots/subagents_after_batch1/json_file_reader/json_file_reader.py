import json
import os
from tools import execute_shell_command


def main(query: str) -> dict:
    # Find JSON files in the workspace and report their contents (bounded output).
    ls = execute_shell_command('ls -1 *.json 2>/dev/null')
    files = [x.strip() for x in ls.splitlines() if x.strip()]
    report = {}
    for fn in files:
        try:
            with open(fn, 'r', encoding='utf-8', errors='replace') as f:
                data = json.load(f)
            if isinstance(data, dict) and 'items' in data:
                items = data['items']
                report[fn] = {
                    'num_items': len(items),
                    'sample': items[:25],
                    'source': data.get('source'),
                }
            else:
                report[fn] = {'type': type(data).__name__, 'preview': str(data)[:800]}
        except Exception as e:
            report[fn] = {'error': str(e)}
    ans = json.dumps(report, ensure_ascii=False)
    return {'answer': ans, 'summary': 'Read JSON files: ' + ', '.join(files) + '. ' + ans[:1500]}
