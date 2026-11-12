
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

with open('plot_payload.json') as f:
    payload = json.load(f)
series = payload['series']
spec = payload['spec']
sf = spec.get('scale_factor', 1) or 1

fig, ax = plt.subplots(figsize=(12, 6.5))
for s in series:
    xs = [p[0] for p in s['points']]
    ys = [p[1] / sf for p in s['points']]
    label = s['name'] + (' (' + s['unit'] + ')' if s.get('unit') else '')
    if spec.get('chart_type') == 'bar':
        ax.bar(xs, ys, width=0.8, label=label)
    else:
        ax.plot(xs, ys, marker='o', markersize=4, linewidth=1.6, label=label)

ax.set_title(spec.get('title', 'Chart'), fontsize=14, fontweight='bold')
ax.set_xlabel(spec.get('xlabel', 'Year'))
ax.set_ylabel(spec.get('ylabel', 'Value'))
if spec.get('y_scale') == 'log':
    ax.set_yscale('log')
ax.grid(True, alpha=0.3, linestyle='--')
if len(series) > 1:
    ax.legend()
fig.tight_layout()
fig.savefig('population_chart.png', dpi=150)
print('saved population_chart.png')
