import json
import re
import os
from llm import call_llm
from tools import execute_shell_command


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


def main(query: str) -> dict:
    logic = []
    catalog = (
        "Available Our World in Data CSV datasets:\n"
        "- co2 -> https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv (columns: country, year, co2, co2_per_capita, total_ghg)\n"
        "- energy -> https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv (columns: country, year, renewables_share_energy, low_carbon_share_energy)\n"
    )
    plan = call_llm(
        system=(
            "You are a data acquisition planner. Given a research query about country-level CO2 emissions "
            "and/or renewable energy shares, decide: 1) list of countries (OWID spelling e.g. 'United States','China','Germany','India','Brazil'), "
            "2) metrics to extract mapped to columns in known CSV datasets, 3) start and end year. "
            "Return ONLY JSON: {'countries':[...], 'datasets':{'key':{'url':'...','columns':[...]}}, "
            "'metrics':[{'name':'CO2 emissions','dataset_key':'co2','column':'co2'},{'name':'Renewable share','dataset_key':'energy','column':'renewables_share_energy'}], "
            "'start_year':1990,'end_year':2022}. Use ONLY these URLs: co2 -> https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv ; energy -> https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv . "
            "If query lacks details, choose major emitters (China, United States, India, Germany, Brazil) and years 1990-2022."
        ),
        messages=[{'role': 'user', 'content': 'Research query: ' + str(query) + '\n\n' + catalog}],
        max_tokens=1500,
    )
    spec = _parse_json(plan)
    if not isinstance(spec, dict):
        spec = {}
    countries = spec.get('countries') or ['China', 'United States', 'India', 'Germany', 'Brazil']
    start_year = int(spec.get('start_year', 1990) or 1990)
    end_year = int(spec.get('end_year', 2022) or 2022)
    datasets = spec.get('datasets') or {
        'co2': {'url': 'https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv', 'columns': ['co2']},
        'energy': {'url': 'https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv', 'columns': ['renewables_share_energy']},
    }
    metrics = spec.get('metrics') or [
        {'name': 'CO2 emissions (Mt)', 'dataset_key': 'co2', 'column': 'co2'},
        {'name': 'Renewable share of energy (%)', 'dataset_key': 'energy', 'column': 'renewables_share_energy'},
    ]
    logic.append('Plan: countries=%s years=%s-%s metrics=%s' % (countries, start_year, end_year, [m.get('name') for m in metrics]))
    local_files = {}
    for key, ds in datasets.items():
        url = ds.get('url')
        fname = 'owid_' + re.sub(r'[^a-zA-Z0-9]', '_', str(key)) + '.csv'
        if not os.path.exists(fname) or os.path.getsize(fname) < 1000:
            dl = execute_shell_command('curl -sL --max-time 180 "%s" -o %s 2>&1; echo DONE; ls -la %s' % (url, fname, fname))
            logic.append('Download %s: %s' % (url, str(dl).strip()[-300:]))
        else:
            logic.append('Reuse cached ' + fname)
        local_files[key] = fname
    for key, fname in local_files.items():
        hdr = execute_shell_command('head -n 1 %s' % fname)
        logic.append('Header[%s]: %s' % (key, str(hdr).strip()[:400]))
    extract_script = r'''
import json, sys
spec = json.load(open('fetch_spec.json'))
countries = spec['countries']
start = spec['start_year']; end = spec['end_year']
metrics = spec['metrics']
datasets = spec['datasets']
local_files = spec['local_files']
result = {'countries': countries, 'start_year': start, 'end_year': end, 'metrics': metrics}
try:
    import pandas as pd
except Exception as e:
    print(json.dumps({'error': 'no pandas: '+str(e)})); sys.exit(0)
out = {c: {} for c in countries}
for m in metrics:
    key = m['dataset_key']; col = m['column']; name = m['name']
    fname = local_files.get(key)
    if not fname:
        continue
    try:
        df = pd.read_csv(fname, usecols=lambda x: x in ['country','year',col])
    except Exception as e:
        print('read fail '+str(key)+': '+str(e)); continue
    col2 = col
    if col not in df.columns:
        cand = [c for c in df.columns if col.lower() in c.lower()]
        if cand: col2 = cand[0]
        else: continue
    df = df[df['country'].isin(countries)]
    df = df[(df['year'] >= start) & (df['year'] <= end)]
    for _, row in df.iterrows():
        c = row['country']; y = int(row['year'])
        if c not in out: out[c] = {}
        if y not in out[c]: out[c][y] = {}
        try:
            v = float(row[col2])
            if v == v:
                out[c][y][name] = v
        except Exception:
            pass
rows = []
for c in countries:
    for y in sorted(out.get(c, {}).keys()):
        entry = {'country': c, 'year': y}
        entry.update(out[c][y])
        rows.append(entry)
result['rows'] = rows
result['n_rows'] = len(rows)
json.dump(result, open('fetched_data.json','w'), indent=2)
print('WROTE fetched_data.json rows=%d' % len(rows))
'''
    fetch_spec = {'countries': countries, 'start_year': start_year, 'end_year': end_year,
                  'metrics': metrics, 'datasets': datasets, 'local_files': local_files}
    with open('fetch_spec.json', 'w') as f:
        json.dump(fetch_spec, f, indent=2)
    with open('extract_data.py', 'w') as f:
        f.write(extract_script)
    pk = execute_shell_command('python -c "import pandas; print(pandas.__version__)"')
    if 'Error' in str(pk) or 'No module' in str(pk):
        execute_shell_command('pip install pandas 2>&1 | tail -n 2')
    run = execute_shell_command('python extract_data.py 2>&1')
    logic.append('Extract run: ' + str(run).strip()[:500])
    n_rows = 0
    try:
        with open('fetched_data.json') as f:
            result = json.load(f)
        n_rows = result.get('n_rows', len(result.get('rows', [])))
    except Exception as e:
        logic.append('Could not load fetched_data.json: ' + str(e))
    summary = call_llm(
        system='You are a data acquisition summarizer. Write a concise SUMMARY (100-500 words) of what data was downloaded, from which sources, for which countries/years, and any issues.',
        messages=[{'role': 'user', 'content': 'Query: ' + str(query) + '\nLog:\n' + '\n'.join(logic) + '\n\nRows fetched: %s' % n_rows}],
        max_tokens=1200,
    )
    if n_rows > 0:
        answer = ('Downloaded %d country-year rows into fetched_data.json for countries=%s, years=%s-%s, metrics=%s.'
                  % (n_rows, countries, start_year, end_year, [m.get('name') for m in metrics]))
    else:
        answer = 'FAILED to extract data. ' + ' | '.join(logic[-3:])
    return {'answer': answer, 'summary': summary}
