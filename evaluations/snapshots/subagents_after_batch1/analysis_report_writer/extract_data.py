
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
