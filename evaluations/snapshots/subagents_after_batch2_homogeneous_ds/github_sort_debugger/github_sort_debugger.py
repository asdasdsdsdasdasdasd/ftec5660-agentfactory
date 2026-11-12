import json
from llm import call_llm


def _get(url):
    import urllib.request
    req = urllib.request.Request(url, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'dbg'})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.loads(r.read().decode('utf-8', 'replace'))
    except Exception as e:
        return {'error': str(e)}


def main(query: str) -> dict:
    ev = []
    # Test default vs sort=stars ordering
    d1 = _get('https://api.github.com/orgs/facebookresearch/repos?per_page=10')
    if isinstance(d1, list):
        ev.append('DEFAULT per_page=10 order: ' + json.dumps([(x['name'], x.get('stargazers_count')) for x in d1]))
    # Test sort=stars
    d2 = _get('https://api.github.com/orgs/facebookresearch/repos?per_page=10&sort=stars&direction=desc')
    if isinstance(d2, list):
        ev.append('sort=stars order: ' + json.dumps([(x['name'], x.get('stargazers_count')) for x in d2]))
    # Search API sorted by stars (scoped to org)
    d3 = _get('https://api.github.com/search/repositories?q=org:facebookresearch&sort=stars&order=desc&per_page=10')
    if isinstance(d3, dict) and 'items' in d3:
        ev.append('search API top: ' + json.dumps([(x['name'], x.get('stargazers_count')) for x in d3['items']]))
    else:
        ev.append('search API returned: ' + json.dumps(d3)[:300])
    # Try ALL pages default order and find top-starred client-side
    allrepos = []
    for page in range(1, 16):
        dd = _get('https://api.github.com/orgs/facebookresearch/repos?per_page=100&page=' + str(page))
        if isinstance(dd, list) and dd:
            allrepos.extend(dd)
        else:
            break
    allrepos = [r for r in allrepos if isinstance(r, dict) and not r.get('fork')]
    allrepos.sort(key=lambda r: r.get('stargazers_count') or 0, reverse=True)
    ev.append('TOTAL nonfork fetched: ' + str(len(allrepos)))
    ev.append('CLIENT-SIDE top 10 by stars: ' + json.dumps([(r['name'], r.get('stargazers_count')) for r in allrepos[:10]]))

    full = '\n'.join(ev)
    summary = call_llm(
        system='Analyze which ordering the GitHub API honors and confirm the most reliable way to get an org top-starred repos.',
        messages=[{'role': 'user', 'content': full}],
        max_tokens=1500,
    )
    return {'answer': full[:3000], 'summary': summary}
