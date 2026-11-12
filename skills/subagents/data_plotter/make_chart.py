
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

d = json.load(open('plot_data.json'))
spec = d['spec']
pts = d['points']
series_order = []
for p in pts:
    if p['series'] not in series_order:
        series_order.append(p['series'])

fig, ax = plt.subplots(figsize=(14, 8))
ct = spec.get('chart_type', 'line')
for s in series_order:
    sub = [p for p in pts if p['series'] == s]
    xs = [p['x'] for p in sub]
    ys = [p['y'] for p in sub]
    lbl = None if (s == 'default') else s
    if ct == 'bar':
        ax.bar([str(x) for x in xs], ys, label=lbl)
    elif ct == 'scatter':
        ax.scatter(xs, ys, label=lbl)
    else:
        ax.plot(xs, ys, marker='o', label=lbl, linewidth=1.8)

ax.set_title(spec.get('title', 'Chart'), fontsize=15, fontweight='bold')
ax.set_xlabel(spec.get('x_label', 'X'), fontsize=12)
ax.set_ylabel(spec.get('y_label', 'Y'), fontsize=12)
ax.grid(True, alpha=0.3)
if len(series_order) > 1:
    ax.legend()
plt.xticks(rotation=45, ha='right')
fig.tight_layout()
fig.savefig('population_chart.png', dpi=130)
print('SAVED population_chart.png with', len(pts), 'points')
