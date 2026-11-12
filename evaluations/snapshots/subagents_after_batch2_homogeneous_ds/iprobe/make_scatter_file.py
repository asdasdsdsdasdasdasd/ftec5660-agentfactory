
import json, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

d = json.load(open('plot_input.json'))
x = np.array(d['x']); y = np.array(d['y']); labels = d['labels']; spec = d['spec']
fig, ax = plt.subplots(figsize=(10, 6.5))
ax.scatter(x, y, s=55, color='#1f77b4', edgecolor='black', linewidth=0.4, alpha=0.8, label='Observations')
for xi, yi in zip(x, y):
    ax.annotate('', xy=(xi, yi))
slope, intercept = np.polyfit(x, y, 1)
r = np.corrcoef(x, y)[0, 1]
r2 = r * r
xfit = np.linspace(x.min(), x.max(), 100)
ax.plot(xfit, slope * xfit + intercept, color='red', linewidth=2, label='OLS fit: y = %.4g x + %.4g\nR2 = %.4f, r = %.4f' % (slope, intercept, r2, r))
ax.set_xlabel(spec.get('x_label', 'X'))
ax.set_ylabel(spec.get('y_label', 'Y'))
ax.set_title(spec.get('title', 'Scatter with Regression'))
ax.grid(True, alpha=0.3)
ax.legend(loc='best')
txt = 'Slope=%.4g\nIntercept=%.4g\nR^2=%.4f\nr=%.4f\nn=%d' % (slope, intercept, r2, r, len(x))
ax.text(0.02, 0.98, txt, transform=ax.transAxes, va='top', fontsize=9, bbox=dict(boxstyle='round', fc='wheat', alpha=0.6))
plt.tight_layout()
plt.savefig('scatter_regression.png', dpi=150)
print('SAVED scatter_regression.png')
print('FIT slope=%.6g intercept=%.6g r2=%.6f r=%.6f n=%d' % (slope, intercept, r2, r, len(x)))
