import json
from llm import call_llm
from tools import execute_shell_command


def probe_url(url, tag):
    script = [
        'import json, urllib.request',
        'url = ' + repr(url),
        'import time',
        'd = None; err = ""',
        'for a in range(6):',
        '    try:',
        '        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})',
        '        d = json.loads(urllib.request.urlopen(req, timeout=90).read().decode("utf-8"))',
        '        if isinstance(d, list) and len(d) > 1 and d[1]:',
        '            break',
        '        err = str(d)[:150]',
        '    except Exception as e:',
        '        err = str(e); d = None',
        '    time.sleep(4 + 3*a)',
        'try:',
        '    meta = d[0] if isinstance(d, list) and d else {}',
        '    rows = d[1] if isinstance(d, list) and len(d) > 1 and d[1] else []',
        '    nonzero = [r for r in rows if r.get("value") is not None]',
        '    print("ROWS", len(rows), "NONNULL", len(nonzero), "ERR", err)',
        '    print("SAMPLE", json.dumps([{"date": r.get("date"), "value": r.get("value")} for r in rows[:6]]))',
        'except Exception as e:',
        '    print("FATAL", str(e), err)',
    ]
    fn = 'ip_' + tag + '.py'
    with open(fn, 'w') as f:
        f.write('\n'.join(script) + '\n')
    return str(execute_shell_command('python "%s"' % fn)).strip()


def main(query: str) -> dict:
    plan = call_llm(
        system='You catalog World Bank indicator codes. Given a data request, list candidate World Bank indicator codes (and country ISO3) that plausibly provide the requested series. Return ONLY JSON {"targets":[{"label":"...","country":"USA","indicator":"CODE"}]} with 2-4 candidates.',
        messages=[{'role': 'user', 'content': query}], max_tokens=600)
    import re
    try:
        targets = json.loads(re.search(r'\{.*\}', plan, re.DOTALL).group(0)).get('targets', [])
    except Exception:
        targets = []
    ev = []
    for i, t in enumerate(targets):
        country = t.get('country', 'USA')
        ind = t.get('indicator')
        if not ind:
            continue
        url = 'https://api.worldbank.org/v2/country/%s/indicator/%s?format=json&per_page=200&date=2000:2022' % (country, ind)
        out = probe_url(url, 't%d' % i)
        ev.append('%s [%s] =>\n%s' % (t.get('label'), ind, out))
    summary = call_llm(
        system='Report which World Bank indicator codes returned non-null US data for 2000-2022. For each, state ROWS/NONNULL counts and sample values. Identify the best indicator that gives current health expenditure for the US.',
        messages=[{'role': 'user', 'content': 'Query: ' + query + '\nEvidence:\n' + '\n\n'.join(ev)}], max_tokens=1500)
    return {'answer': '\n\n'.join(ev), 'summary': summary}
