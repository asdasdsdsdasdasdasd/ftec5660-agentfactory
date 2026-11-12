import json
from tools import execute_shell_command


def main(query: str) -> dict:
    # query format: 'oldname -> newname'
    try:
        old, new = [s.strip() for s in query.split('->')]
    except Exception:
        return {'answer': 'Bad query, use: old -> new', 'summary': 'parse fail'}
    out = execute_shell_command('mv ' + old + ' ' + new + ' 2>&1; ls *.py 2>&1')
    return {'answer': str(out)[:2000], 'summary': 'renamed ' + old + ' to ' + new + ' | ' + str(out)[:500]}
