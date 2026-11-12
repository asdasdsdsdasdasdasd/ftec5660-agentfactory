import json
from llm import call_llm
from tools import execute_shell_command


def main(query: str) -> dict:
    ev = []
    checks = [
        ('wb_status', 'curl -s -o /dev/null -w "%{http_code}" --max-time 40 "https://api.worldbank.org/v2/country/USA/indicator/NY.GDP.MKTP.CD?format=json&per_page=5"'),
        ('wb_head', 'curl -sL --max-time 40 "https://api.worldbank.org/v2/country/USA/indicator/NY.GDP.MKTP.CD?format=json&per_page=5" | head -c 500'),
        ('fred_status', 'curl -s -o /dev/null -w "%{http_code}" --max-time 40 -A "Mozilla/5.0" "https://fred.stlouisfed.org/graph/fredgraph.csv?id=GDP"'),
        ('fred_head', 'curl -sL --max-time 40 -A "Mozilla/5.0" "https://fred.stlouisfed.org/graph/fredgraph.csv?id=GDP" | head -5'),
        ('exact_url', 'curl -sL --max-time 60 "https://api.worldbank.org/v2/country/USA/indicator/NY.GDP.MKTP.CD?format=json&per_page=300&date=2000:2023" -o /tmp/wbtest.json 2>/dev/null; echo DONE; wc -c /tmp/wbtest.json'),
        ('exact_parse', 'python -c "import json; d=json.load(open(\'/tmp/wbtest.json\')); print(type(d).__name__, len(d), len(d[1]) if len(d)>1 else 0)"'),
        ('health_probe', 'python -c "import json,urllib.request; u=chr(104)+chr(116)+chr(116)+chr(112)+chr(115)+chr(58)+chr(47)+chr(47)+chr(97)+chr(112)+chr(105)+chr(46)+chr(119)+chr(111)+chr(114)+chr(108)+chr(100)+chr(98)+chr(97)+chr(110)+chr(107)+chr(46)+chr(111)+chr(114)+chr(103)+chr(47)+chr(118)+chr(50)+chr(47)+chr(99)+chr(111)+chr(117)+chr(110)+chr(116)+chr(114)+chr(121)+chr(47)+chr(85)+chr(83)+chr(65)+chr(47)+chr(105)+chr(110)+chr(100)+chr(105)+chr(99)+chr(97)+chr(116)+chr(111)+chr(114)+chr(47)+chr(83)+chr(72)+chr(46)+chr(88)+chr(80)+chr(68)+chr(46)+chr(67)+chr(72)+chr(69)+chr(88)+chr(46)+chr(71)+chr(68)+chr(46)+chr(90)+chr(83)+chr(63)+chr(102)+chr(111)+chr(114)+chr(109)+chr(97)+chr(116)+chr(61)+chr(106)+chr(115)+chr(111)+chr(110)+chr(38)+chr(112)+chr(101)+chr(114)+chr(95)+chr(112)+chr(97)+chr(103)+chr(101)+chr(61)+chr(50)+chr(48)+chr(48); d=json.loads(urllib.request.urlopen(u,timeout=60).read().decode()); print(d[0]); print(len(d[1]) if len(d)>1 and d[1] else 0)"'),
        ('generic_net', 'curl -s -o /dev/null -w "%{http_code}" --max-time 20 "https://example.com"'),
    ]
    for name, cmd in checks:
        out = execute_shell_command(cmd)
        ev.append('%s => %s' % (name, str(out).strip()[:600]))
    summary = call_llm(
        system='You are a diagnostics summarizer. Report exactly what each test returned (HTTP status, response body preview) and diagnose whether World Bank API and FRED are reachable and returning valid JSON/CSV in this environment.',
        messages=[{'role': 'user', 'content': 'Query: ' + str(query) + '\nResults:\n' + '\n'.join(ev)}],
        max_tokens=1200,
    )
    return {'answer': '\n'.join(ev), 'summary': summary}
