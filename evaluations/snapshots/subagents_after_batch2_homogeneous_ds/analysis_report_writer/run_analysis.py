
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
