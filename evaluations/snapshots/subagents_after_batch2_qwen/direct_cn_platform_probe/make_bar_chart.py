
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# Try to pick a font that supports CJK so non-Latin keywords render correctly.
cjk_candidates = ['Noto Sans CJK JP', 'Noto Sans CJK SC', 'Noto Sans JP', 'WenQuanYi Zen Hei', 'WenQuanYi Micro Hei', 'IPAGothic', 'Source Han Sans', 'SimHei', 'Microsoft YaHei', 'MS Gothic']
avail = {f.name for f in fm.fontManager.ttflist}
chosen = None
for c in cjk_candidates:
    if c in avail:
        chosen = c
        break
if chosen:
    plt.rcParams['font.sans-serif'] = [chosen] + list(plt.rcParams.get('font.sans-serif', []))
    plt.rcParams['axes.unicode_minus'] = False

d = json.load(open('chart_items.json', encoding='utf-8'))
items = d['items']
title = d['title']; xl = d['x_label']; yl = d['y_label']; horizontal = d.get('horizontal', True)
labels = [it['keyword'] for it in items]
vals = [it['count'] for it in items]

fig, ax = plt.subplots(figsize=(13, 9))
colors = plt.cm.viridis([i/ max(len(vals)-1,1) for i in range(len(vals))])
if horizontal:
    # largest at top -> reverse so biggest on top of horizontal barh
    ypos = list(range(len(labels)))[::-1]
    ax.barh(ypos, vals, color=colors)
    ax.set_yticks(ypos)
    ax.set_yticklabels(labels)
    ax.set_xlabel(yl)
    ax.set_ylabel(xl)
    for yp, v in zip(ypos, vals):
        ax.text(v, yp, ' ' + ('%g' % v), va='center', fontsize=8)
else:
    ax.bar(range(len(labels)), vals, color=colors)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha='right')
    ax.set_xlabel(xl)
    ax.set_ylabel(yl)
ax.set_title(title, fontsize=15, fontweight='bold')
ax.grid(True, axis='x' if horizontal else 'y', alpha=0.3)
fig.tight_layout()
fig.savefig('trending_keywords_bar_chart.png', dpi=130)
print('SAVED trending_keywords_bar_chart.png with', len(items), 'bars')
