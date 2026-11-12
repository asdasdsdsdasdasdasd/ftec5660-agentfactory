import json
import re
from llm import call_llm
from tools import execute_shell_command, search_serper


def _parse_json(text):
    t = (text or '').strip()
    t = re.sub(r'^```(?:json)?', '', t).strip()
    t = re.sub(r'```$', '', t).strip()
    try:
        return json.loads(t)
    except Exception:
        pass
    m = re.search(r'[\[\{].*[\]\}]', t, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


def fetch_worldbank(country, indicator, start, end, name, logic):
    url = ('https://api.worldbank.org/v2/country/%s/indicator/%s?format=json&per_page=300&date=%s:%s'
           % (country, indicator, start, end))
    vals = {}
    out_fname = 'wbout_' + re.sub(r'[^a-zA-Z0-9]', '_', str(name)) + '.json'
    helper = (
        'import json,urllib.request\n'
        'url=%r\n'
        'vals={}\n'
        'try:\n'
        '    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})\n'
        '    d=json.loads(urllib.request.urlopen(req,timeout=60).read().decode("utf-8"))\n'
        '    if isinstance(d,list) and len(d)>1 and d[1]:\n'
        '        for rec in d[1]:\n'
        '            v=rec.get("value"); y=rec.get("date")\n'
        '            if v is not None and y:\n'
        '                try: vals[int(y)]=float(v)\n'
        '                except: pass\n'
        'except Exception as e:\n'
        '    vals={"_error":str(e)}\n'
        'json.dump(vals,open(%r,"w"))\n'
    ) % (url, out_fname)
    helper = helper.replace('\n', ' ')
    pyf = 'wbhelper_' + re.sub(r'[^a-zA-Z0-9]', '_', str(name)) + '.py'
    try:
        with open(pyf, 'w') as f:
            f.write(helper.replace('; ', '\n').replace('vals={', 'vals={') if False else helper.replace(' )', ')'))
    except Exception:
        pass
    # Write helper script cleanly
    script_lines = [
        'import json, urllib.request',
        'url = ' + repr(url),
        'vals = {}',
        'import time',
        'd = None',
        'last_err = ""',
        'for attempt in range(8):',
        '    try:',
        '        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})',
        '        d = json.loads(urllib.request.urlopen(req, timeout=90).read().decode("utf-8"))',
        '        if isinstance(d, list) and len(d) > 1 and d[1]:',
        '            break',
        '        last_err = str(d)[:100]',
        '    except Exception as e:',
        '        last_err = str(e)',
        '        d = None',
        '    time.sleep(4 + 3 * attempt)',
        'try:',
        '    if isinstance(d, list) and len(d) > 1 and d[1]:',
        '        for rec in d[1]:',
        '            v = rec.get("value"); y = rec.get("date")',
        '            if v is not None and y:',
        '                try:',
        '                    vals[int(y)] = float(v)',
        '                except Exception:',
        '                    pass',
        'except Exception as e:',
        '    vals = {"_error": str(e)}',
        'if not vals:',
        '    vals = {"_error": last_err or "no data returned"}',
        'try:',
        '    json.dump(vals, open(' + repr(out_fname) + ', "w"))',
        'except Exception as we:',
        '    open(' + repr(out_fname) + ', "w").write("{}")',
    ]
    with open(pyf, 'w') as f:
        f.write('\n'.join(script_lines) + '\n')
    execute_shell_command('python "%s"' % pyf)
    try:
        loaded = json.load(open(out_fname))
        if isinstance(loaded, dict) and '_error' in loaded:
            logic.append('WB error %s: %s' % (name, loaded['_error']))
        else:
            vals = loaded
    except Exception as e:
        logic.append('WB load fail %s: %s' % (name, e))
    logic.append('WB %s (%s/%s): %d points' % (name, country, indicator, len(vals)))
    return vals


def fetch_fred(fred_id, name, logic):
    url = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=' + fred_id
    fname = 'fred_' + re.sub(r'[^a-zA-Z0-9]', '_', str(name)) + '.csv'
    execute_shell_command('curl -sL --max-time 60 -A "Mozilla/5.0" "%s" -o %s' % (url, fname))
    vals = {}
    try:
        with open(fname) as f:
            f.readline()
            for line in f:
                parts = line.strip().split(',')
                if len(parts) < 2:
                    continue
                date, val = parts[0], parts[1]
                if val in ('', '.', 'NaN'):
                    continue
                ym = re.match(r'(\d{4})', date)
                if ym:
                    try:
                        vals[int(ym.group(1))] = float(val)
                    except Exception:
                        pass
    except Exception as e:
        logic.append('FRED parse fail %s: %s' % (name, e))
    logic.append('FRED %s (%s): %d points' % (name, fred_id, len(vals)))
    return vals


def main(query: str) -> dict:
    logic = []
    plan_prompt = (
        'You are a numeric time-series data planner. Given a query asking to compare numeric annual '
        'series (e.g. expenditure vs GDP), return ONLY JSON: '
        '{"start_year":2000,"end_year":2022,"series":['
        '{"name":"US health expenditure (nominal US$)","world_bank_country":"USA","world_bank_indicator":"","fred_id":""},'
        '{"name":"US GDP (nominal US$)","world_bank_country":"USA","world_bank_indicator":"NY.GDP.MKTP.CD","fred_id":""}]} '
        'Use World Bank indicator codes when possible. Known codes: current health expenditure % of GDP = SH.XPD.CHEX.GD.ZS; '
        'health expenditure per capita current US$ = SH.XPD.CHEX.PC.CD; GDP current US$ = NY.GDP.MKTP.CD; GDP per capita = NY.GDP.PCAP.CD. '
        'FRED ids ok too (e.g. GDP for US nominal GDP, GDPC1 real). Put empty string when unused. '
        'Ensure the two series are on a COMPARABLE basis so a scatter/regression is meaningful '
        '(either both in nominal US$ or both as shares of GDP).'
    )
    plan_raw = call_llm(system=plan_prompt, messages=[{'role': 'user', 'content': 'Query: ' + str(query)}], max_tokens=1200)
    plan = _parse_json(plan_raw) or {}
    logic.append('PLAN: ' + json.dumps(plan)[:800])
    start = plan.get('start_year') or 2000
    end = plan.get('end_year') or 2023

    pk = execute_shell_command('python -c "import pandas; print(pandas.__version__)"')
    if 'Error' in str(pk) or 'No module' in str(pk):
        execute_shell_command('pip install pandas 2>&1 | tail -n 2')

    collected = {}
    for s in plan.get('series', []):
        name = s.get('name') or 'series'
        vals = {}
        if s.get('world_bank_indicator'):
            vals = fetch_worldbank(s.get('world_bank_country', 'USA'), s['world_bank_indicator'], start, end, name, logic)
        if not vals and s.get('fred_id'):
            vals = fetch_fred(s['fred_id'], name, logic)
        if vals:
            collected[name] = vals

    names = list(collected.keys())
    all_years = set()
    for v in collected.values():
        all_years |= set(v.keys())
    rows = []
    for y in sorted(all_years):
        row = {'year': y}
        for n in names:
            if y in collected[n]:
                row[n] = collected[n][y]
        rows.append(row)
    rows = [r for r in rows if isinstance(start, int) is False and True or True]

    out = {'query': query, 'series_names': names, 'rows': rows,
           'start_year': start, 'end_year': end, 'n_series': len(names),
           'n_rows': len(rows), 'log': logic}
    with open('paired_series.json', 'w') as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    summary = call_llm(
        system='Write a concise SUMMARY (100-500 words) of what numeric series were obtained, from which sources, for which years, points per series, and any gaps/issues.',
        messages=[{'role': 'user', 'content': 'Query: ' + str(query) + '\nSeries: ' + json.dumps(names) + '\nRows: %d\nLog:\n%s' % (len(rows), '\n'.join(logic)) + '\nSample: ' + json.dumps(rows[:2]) + ' ... ' + json.dumps(rows[-2:])}],
        max_tokens=1500,
    )
    if rows and len(names) >= 2:
        answer = 'Collected %d aligned rows for %d series (%s) into paired_series.json.' % (len(rows), len(names), names)
    elif rows:
        answer = 'Collected %d series (%s) with %d rows; missing a second series. Log: %s' % (len(names), names, len(rows), ' | '.join(logic[-3:]))
    else:
        answer = 'FAILED to collect numeric data. Log: ' + ' | '.join(logic[-4:])
    return {'answer': answer, 'summary': summary}
