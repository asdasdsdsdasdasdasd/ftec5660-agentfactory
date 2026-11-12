import json
import os
import re
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
    # LLM: extract input json filename, the two metric column names, entity key, time key, chart title/axes
    plan = call_llm(
        system=(
            "You are an analysis planner. The user wants correlation/trend analysis between two numeric metrics "
            "stored in a JSON file of tidy rows. Extract config. Return ONLY JSON with keys: "
            "'input_file', 'entity_key' (e.g. country), 'time_key' (e.g. year), "
            "'metric_x' (first metric column name exact), 'metric_y' (second metric column name exact), "
            "'x_label','y_label','title'. If uncertain about exact column names use the wording from query."
        ),
        messages=[{'role': 'user', 'content': 'Query: ' + str(query)}],
        max_tokens=500,
    )
    cfg = _parse_json(plan) or {}
    input_file = cfg.get('input_file') or 'fetched_data.json'
    entity_key = cfg.get('entity_key') or 'country'
    time_key = cfg.get('time_key') or 'year'
    metric_x = cfg.get('metric_x') or 'Renewable share'
    metric_y = cfg.get('metric_y') or 'CO2 emissions'
    x_label = cfg.get('x_label') or metric_x
    y_label = cfg.get('y_label') or metric_y
    title = cfg.get('title') or 'Analysis'
    logic.append('Config: %s' % json.dumps(cfg))

    if not os.path.exists(input_file):
        return {'answer': 'Input file not found: ' + input_file, 'summary': 'Missing input.'}

    # Install deps
    pk = execute_shell_command('python -c "import pandas, matplotlib, numpy; print(1)"')
    if 'Error' in str(pk) or 'No module' in str(pk):
        execute_shell_command('pip install pandas matplotlib numpy 2>&1 | tail -n 2')

    analysis_script = r'''
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

cfg = json.load(open('analysis_cfg.json'))
input_file = cfg['input_file']; entity_key = cfg['entity_key']; time_key = cfg['time_key']
mx = cfg['metric_x']; my = cfg['metric_y']
d = json.load(open(input_file))
rows = d.get('rows', [])
df = pd.DataFrame(rows)
# resolve columns (fuzzy fallback)
def resolve(df, name):
    if name in df.columns: return name
    for c in df.columns:
        if name.lower() in c.lower() or c.lower() in name.lower(): return c
    return None
cx = resolve(df, mx); cy = resolve(df, my)
if cx is None or cy is None:
    print('COLUMN_ERROR columns=%s needed=%s,%s' % (list(df.columns), mx, my)); raise SystemExit
mx, my = cx, cy
results = {'entity_key': entity_key, 'time_key': time_key, 'metric_x': mx, 'metric_y': my, 'entities': {}}
# pooled correlation
df2 = df[[mx, my]].dropna()
pooled_r = float(np.corrcoef(df2[mx], df2[my])[0,1]) if len(df2) > 2 else None
# pooled regression
if len(df2) > 2:
    slope, intercept = np.polyfit(df2[mx], df2[my], 1)
    pred = slope*df2[mx]+intercept
    ss_res = float(((df2[my]-pred)**2).sum()); ss_tot = float(((df2[my]-df2[my].mean())**2).sum())
    r2 = 1 - ss_res/ss_tot if ss_tot>0 else None
else:
    slope=intercept=r2=None
results['pooled'] = {'pearson_r': pooled_r, 'slope': (float(slope) if slope is not None else None),
                     'intercept': (float(intercept) if intercept is not None else None),
                     'r_squared': (float(r2) if r2 is not None else None), 'n': int(len(df2))}

# per-entity trend and correlation
for ent, g in df.groupby(entity_key):
    g = g.sort_values(time_key)
    gu = g[[time_key, mx, my]].dropna()
    info = {'start_year': None, 'end_year': None}
    if len(gu) >= 2:
        info['start_year'] = int(gu[time_key].iloc[0]); info['end_year'] = int(gu[time_key].iloc[-1])
        info['metric_x_start'] = float(gu[mx].iloc[0]); info['metric_x_end'] = float(gu[mx].iloc[-1])
        info['metric_y_start'] = float(gu[my].iloc[0]); info['metric_y_end'] = float(gu[my].iloc[-1])
        info['metric_x_pct_change'] = float((gu[mx].iloc[-1]-gu[mx].iloc[0])/abs(gu[mx].iloc[0])*100) if gu[mx].iloc[0]!=0 else None
        info['metric_y_pct_change'] = float((gu[my].iloc[-1]-gu[my].iloc[0])/abs(gu[my].iloc[0])*100) if gu[my].iloc[0]!=0 else None
        if len(gu) > 2 and gu[mx].std()>0 and gu[my].std()>0:
            info['within_country_r'] = float(np.corrcoef(gu[mx], gu[my])[0,1])
    results['entities'][str(ent)] = info

json.dump(results, open('analysis_results.json','w'), indent=2)

# Plot 1: time series of both metrics per country (dual subplots)
ents = sorted(df[entity_key].unique())
fig, axes = plt.subplots(2, 1, figsize=(13, 9), sharex=True)
for ent in ents:
    g = df[df[entity_key]==ent].sort_values(time_key)
    axes[0].plot(g[time_key], g[my], marker='', label=str(ent), linewidth=1.8)
    axes[1].plot(g[time_key], g[mx], marker='', label=str(ent), linewidth=1.8)
axes[0].set_ylabel(str(my)); axes[0].set_title(str(my)+' over time'); axes[0].legend(fontsize=8); axes[0].grid(alpha=0.3)
axes[1].set_ylabel(str(mx)); axes[1].set_title(str(mx)+' over time'); axes[1].legend(fontsize=8); axes[1].grid(alpha=0.3)
axes[1].set_xlabel(str(time_key))
fig.suptitle(cfg.get('title','Trends'), fontweight='bold')
fig.tight_layout(); fig.savefig('trends_plot.png', dpi=130); plt.close(fig)

# Plot 2: scatter of metric_x vs metric_y with pooled regression
fig, ax = plt.subplots(figsize=(11, 8))
colors = plt.cm.tab10(np.linspace(0,1,len(ents)))
for i, ent in enumerate(ents):
    g = df[df[entity_key]==ent]
    ax.scatter(g[mx], g[my], label=str(ent), color=colors[i], s=25, alpha=0.8)
if results['pooled']['slope'] is not None:
    xs = np.linspace(df2[mx].min(), df2[mx].max(), 100)
    ys = results['pooled']['slope']*xs + results['pooled']['intercept']
    ax.plot(xs, ys, 'k--', label='Pooled OLS (r=%.3f, R2=%.3f)' % (results['pooled']['pearson_r'], results['pooled']['r_squared']))
ax.set_xlabel(cfg.get('x_label', mx)); ax.set_ylabel(cfg.get('y_label', my))
ax.set_title('Correlation: ' + str(mx) + ' vs ' + str(my), fontweight='bold')
ax.legend(fontsize=8); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig('correlation_scatter.png', dpi=130); plt.close(fig)
print('ANALYSIS_OK pooled_r=%s r2=%s entities=%d' % (results['pooled']['pearson_r'], results['pooled']['r_squared'], len(ents)))
'''
    with open('analysis_cfg.json', 'w') as f:
        json.dump({'input_file': input_file, 'entity_key': entity_key, 'time_key': time_key,
                   'metric_x': metric_x, 'metric_y': metric_y, 'x_label': x_label, 'y_label': y_label, 'title': title}, f)
    with open('run_analysis.py', 'w') as f:
        f.write(analysis_script)
    out = execute_shell_command('python run_analysis.py 2>&1')
    logic.append('Analysis run: ' + str(out).strip()[:600])

    res = {}
    if os.path.exists('analysis_results.json'):
        with open('analysis_results.json') as f:
            res = json.load(f)
    plots = [p for p in ['trends_plot.png', 'correlation_scatter.png'] if os.path.exists(p)]
    logic.append('Plots: %s' % plots)

    # LLM insight summary
    summary = call_llm(
        system=('You are an environmental data analyst. Using the quantitative results, write a thorough SUMMARY (200-800 words) of the correlation and trends: '
                'report pooled Pearson r and R2, direction of relationship, per-country within-country correlations, which countries decoupled (renewables rose while emissions fell) vs coupled. Be quantitative and objective.'),
        messages=[{'role': 'user', 'content': 'Query: ' + str(query) + '\n\nAnalysis results JSON:\n' + json.dumps(res)[:4000] + '\n\nRun log:\n' + '\n'.join(logic)}],
        max_tokens=1500,
    )

    answer = 'Analysis complete. Plots generated: ' + str(plots) + '. Pooled r=' + str(res.get('pooled', {}).get('pearson_r')) + ', R2=' + str(res.get('pooled', {}).get('r_squared')) + '. Results in analysis_results.json.'
    return {'answer': answer, 'summary': summary}
