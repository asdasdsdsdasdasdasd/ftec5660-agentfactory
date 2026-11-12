
import json, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

rows = json.loads('[{"period": "Original Bubble Era", "net": -0.583, "total": 12, "pos": 1, "neg": 8, "neu": 3}, {"period": "Post-Crisis Recovery", "net": 0.667, "total": 3, "pos": 2, "neg": 0, "neu": 1}, {"period": "Pandemic Boom", "net": 0.0, "total": 2, "pos": 0, "neg": 0, "neu": 2}, {"period": "Rate Shock & Correction", "net": -0.571, "total": 14, "pos": 1, "neg": 9, "neu": 4}, {"period": "Current Anxiety Period", "net": -0.714, "total": 7, "pos": 1, "neg": 6, "neu": 0}]')
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
ax1.set_title('Public Sentiment Toward the Housing Price Bubble Over Time')
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
plt.savefig('sentiment_trend.png', dpi=130)
print('chart saved')
