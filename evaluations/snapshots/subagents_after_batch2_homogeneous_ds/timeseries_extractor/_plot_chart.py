
import json, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

rows = json.loads('[{"period": "2018-2020", "net": 0.0, "total": 1, "pos": 0, "neg": 0, "neu": 1}, {"period": "2021-2022", "net": -0.75, "total": 4, "pos": 0, "neg": 3, "neu": 1}, {"period": "2023-2024", "net": -0.206, "total": 34, "pos": 7, "neg": 14, "neu": 13}, {"period": "2025-2025", "net": -0.143, "total": 7, "pos": 1, "neg": 2, "neu": 4}]')
labels = [r['period'] for r in rows]
net = [r['net'] for r in rows]
totals = [r['total'] for r in rows]
pos = [r['pos'] for r in rows]
neg = [r['neg'] for r in rows]
neu = [r['neu'] for r in rows]

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8), gridspec_kw={'height_ratios':[2,1]})

# Top: net sentiment line
colors = ['#2e7d32' if v > 0 else '#c62828' if v < 0 else '#757575' for v in net]
ax1.axhline(0, color='#999999', linewidth=1, linestyle='--')
bars = ax1.bar(labels, net, color=colors, alpha=0.75, label='Net sentiment')
ax1.plot(labels, net, color='#1a237e', marker='o', linewidth=2, label='Trend line')
for i, (v, t) in enumerate(zip(net, totals)):
    ax1.text(i, v, f'{v:+.2f}\n(n={t})', ha='center', va='bottom' if v >= 0 else 'top', fontsize=9)
ax1.set_ylabel('Net sentiment (-1 negative .. +1 positive)')
ax1.set_title('Public Sentiment Toward Electric Vehicle Adoption Over Time (2018-2025)')
ax1.legend(loc='upper left')
ax1.set_ylim(min(net + [0]) - 0.3, max(net + [0]) + 0.3)
plt.setp(ax1.get_xticklabels(), rotation=20, ha='right')

# Bottom: stacked counts
ax2.bar(labels, pos, color='#2e7d32', label='Positive')
ax2.bar(labels, neu, bottom=pos, color='#9e9e9e', label='Neutral')
ax2.bar(labels, neg, bottom=[p+n for p,n in zip(pos,neu)], color='#c62828', label='Negative')
ax2.set_ylabel('Item count')
ax2.set_title('Sentiment Composition per Period')
ax2.legend(loc='upper left', fontsize=8)
plt.setp(ax2.get_xticklabels(), rotation=20, ha='right')

plt.tight_layout()
plt.savefig('ev_sentiment_trend.png', dpi=130)
print('chart saved')
