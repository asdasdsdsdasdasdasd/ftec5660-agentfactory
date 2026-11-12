from tools import execute_shell_command, read_url_jina
from llm import call_llm


def main(query: str) -> dict:
    evidence = []

    # Probe 1: raw curl with headers and status code
    cmd = "curl -s -m 30 -w '\nHTTP_CODE:%{http_code}\n' -H 'Accept: application/vnd.github+json' -H 'User-Agent: debug-agent' 'https://api.github.com/orgs/facebookresearch'"
    out = execute_shell_command(cmd)
    evidence.append('PROBE1 curl /orgs/facebookresearch: ' + str(out)[:1500])

    # Probe 2: repos endpoint
    cmd = "curl -s -m 30 -w '\nHTTP_CODE:%{http_code}\n' -H 'Accept: application/vnd.github+json' -H 'User-Agent: debug-agent' 'https://api.github.com/orgs/facebookresearch/repos?sort=stars&per_page=10'"
    out = execute_shell_command(cmd)
    evidence.append('PROBE2 curl /orgs/.../repos: ' + str(out)[:2500])

    # Probe 3: does curl work at all to another site?
    cmd = "curl -s -m 20 -w '\nHTTP_CODE:%{http_code}\n' 'https://api.github.com'"
    out = execute_shell_command(cmd)
    evidence.append('PROBE3 curl api.github.com root: ' + str(out)[:800])

    # Probe 4: read_url_jina on the API URL and on the HTML org page
    for u in ['https://api.github.com/orgs/facebookresearch/repos?sort=stars&per_page=10',
              'https://github.com/facebookresearch']:
        try:
            r = read_url_jina(u)
            if isinstance(r, dict):
                t = r.get('text', '') or str(r)
            else:
                t = str(r)
            evidence.append('PROBE4 read_url_jina ' + u + ' -> ' + t[:2000])
        except Exception as e:
            evidence.append('PROBE4 read_url_jina ' + u + ' ERROR: ' + str(e))

    # Probe 5: check python availability / network via python requests
    cmd = "python3 -c \"import urllib.request,json; r=urllib.request.urlopen('https://api.github.com/orgs/facebookresearch/repos?sort=stars&per_page=10',timeout=30); d=json.load(r); print('N=',len(d)); print(json.dumps([{'name':x['name'],'desc':x.get('description'),'stars':x.get('stargazers_count')} for x in d[:5]],indent=1))\" 2>&1"
    out = execute_shell_command(cmd)
    evidence.append('PROBE5 python urllib: ' + str(out)[:2000])

    full = '\n\n'.join(evidence)
    summary = call_llm(
        system='You are a diagnostic summarizer. Analyze these probe outputs about GitHub API/network access and report concretely: (1) what each probe returned (status codes, sample data), (2) whether api.github.com is reachable via curl and Python, (3) whether read_url_jina can serve GitHub content, and (4) the single most reliable working method to fetch GitHub org description + repos in this environment.',
        messages=[{'role': 'user', 'content': 'Probe evidence:\n' + full}],
        max_tokens=2000,
    )
    return {'answer': full[:3000], 'summary': summary}
