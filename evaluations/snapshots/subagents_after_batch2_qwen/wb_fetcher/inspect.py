import json
from tools import execute_shell_command


def main(query: str) -> dict:
    # query is a filename to read
    out = execute_shell_command('cat -n ' + query + ' 2>&1')
    return {'answer': str(out)[:4000], 'summary': 'cat -n ' + query}
