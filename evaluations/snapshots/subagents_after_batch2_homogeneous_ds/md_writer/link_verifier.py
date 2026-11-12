from llm import call_llm
from tools import execute_shell_command
import re, json


def main(query: str) -> dict:
    # Extract URLs from the query
    urls = re.findall(r'https?://[^\s,\;\)\]]+', query)
    urls = [u.rstrip('.,') for u in urls]
    if not urls:
        return {'answer': 'No URLs found in query.', 'summary': 'No URLs to verify.'}
    results = []
    for u in urls:
        cmd = "curl -s -o /dev/null -w '%{http_code}' -L --max-time 30 '" + u + "'"
        status = execute_shell_command(cmd)
        status = (status or '').strip().split('\n')[-1].strip()
        results.append({'url': u, 'status': status})
    report = '\n'.join(u['url'] + ' -> HTTP ' + u['status'] for u in results)
    summary = call_llm(
        system='Write a short SUMMARY reporting the HTTP status verification results for these links and whether they appear reachable (2xx/3xx).',
        messages=[{'role': 'user', 'content': 'Verification results:\n' + report}],
        max_tokens=600,
    )
    return {'answer': report, 'summary': summary}
