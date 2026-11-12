import json
import os
import re
from llm import call_llm
from tools import execute_shell_command


def main(query: str) -> dict:
    logic = []
    # 1. Find the data file mentioned or default to paired_series.json / scatter_data.json
    fname = 'paired_series.json'
    m = re.search(r'([\w\-]+\.json)', query)
    if m and os.path.exists(m.group(1)):
        fname = m.group(1)
    if not os.path.exists(fname):
        # list json files
        ls = str(execute_shell_command('ls *.json 2>/dev/null'))
        cands = [x for x in ls.split() if x.endswith('.json')]
        if cands:
            fname = cands[0]
        else:
            return {'answer': 'No JSON data file found.', 'summary': 'Looked for paired_series.json / scatter_data.json; none present. ls=' + ls}
    logic.append('Using data file: ' + fname)
    with open(fname) as f:
        data = json.load(f)

    # Normalize rows
    rows = data.get('rows') or data.get('data') or data.get('points') or []
    if not rows and isinstance(data, list):
        rows = data
    logic.append('Loaded %d rows; keys example: %s' % (len(rows), list(rows[0].keys()) if rows else []))

    # 2. LLM decides how to map columns to (x, y) and any derivation
    header = list(rows[0].keys()) if rows else []
    plan_prompt = (
        'You are a data visualization planner. Given a dataset with columns and a user request, decide the '
        'scatter/regression specification. Return ONLY JSON: '
        '{"x_col":"<column name for x>", "y_col":"<column for y>", '
        '"x_label":"...", "y_label":"...", "title":"...", '
        '"derive": "<optional: python expression string using row keys to compute a value, or empty>", '
        '"derive_target": "x|y", "scale": 1.0}'
        ' If the user wants e.g. total expenditure = pct/100*gdp, set derive accordingly and derive_target to the axis '
        'to replace. Choose columns that exist. Keep labels/units clear (e.g. nominal US dollars).'
    )
    plan_raw = call_llm(system=plan_prompt,
                        messages=[{'role': 'user', 'content': 'Request: ' + query + '\nColumns: ' + json.dumps(header) + '\nSample rows: ' + json.dumps(rows[:3])}],
                        max_tokens=800)
    try:
        spec = json.loads(re.search(r'\{.*\}', plan_raw, re.DOTALL).group(0))
    except Exception as e:
        logic.append('Plan parse fail: %s | raw=%s' % (e, plan_raw[:300]))
        spec = {}
    logic.append('SPEC: ' + json.dumps(spec)[:500])

    x_col = spec.get('x_col')
    y_col = spec.get('y_col')
    derive = (spec.get('derive') or '').strip()
    derive_target = spec.get('derive_target') or ''
    scale = spec.get('scale') or 1.0

    # Build (x, y, label) points
    xs, ys, labels = [], [], []
    for r in rows:
        try:
            xv = r.get(x_col)
            yv = r.get(y_col)
            # allow derivation
            if derive:
                # safe eval with row + math
                val = eval(derive, {'__builtins__': {}}, {'row': r, 'abs': abs, 'float': float, 'min': min, 'max': max})
                if derive_target == 'x':
                    xv = val
                else:
                    yv = val
            if xv is None or yv is None:
                continue
            xs.append(float(xv) * (scale if derive_target == 'x' else 1.0))
            ys.append(float(yv) * (scale if derive_target == 'y' else 1.0))
            labels.append(r.get('year') or r.get('date') or r.get('label') or '')
        except Exception as e:
            logic.append('row skip: %s' % e)
    logic.append('Built %d points' % len(xs))

    if len(xs) < 2:
        return {'answer': 'Insufficient points (%d) to plot/regress.' % len(xs), 'summary': '\n'.join(logic)}

    # 3. Write data + a robust plotting script
    with open('plot_input.json', 'w') as f:
        json.dump({'x': xs, 'y': ys, 'labels': labels, 'spec': spec}, f)

    script = r'''
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
'''
    with open('make_scatter_file.py', 'w') as f:
        f.write(script)

    pk = str(execute_shell_command('python -c "import numpy,matplotlib; print("ok")"'))
    if 'ok' not in pk:
        execute_shell_command('pip install numpy matplotlib 2>&1 | tail -n 2')
    run = str(execute_shell_command('python make_scatter_file.py 2>&1'))
    logic.append('RUN: ' + run.strip()[-600:])
    exists = os.path.exists('scatter_regression.png')
    size = os.path.getsize('scatter_regression.png') if exists else 0

    fit = re.search(r'FIT (.+)', run)
    fit_line = fit.group(1) if fit else 'unknown'

    summary = call_llm(
        system='Write a concise SUMMARY (100-400 words) of the scatter+regression produced: what variables were plotted, the OLS fit statistics (slope, intercept, R2, r, n), data source file, and whether the PNG was created.',
        messages=[{'role': 'user', 'content': 'Request: ' + query + '\nLog:\n' + '\n'.join(logic) + '\nPNG exists=%s size=%d\nFit: %s' % (exists, size, fit_line)}],
        max_tokens=1200)

    if exists and size > 1000:
        answer = 'Created scatter_regression.png (%d bytes). OLS fit: %s' % (size, fit_line)
    else:
        answer = 'Failed to create scatter_regression.png. Log: ' + ' | '.join(logic[-4:])
    return {'answer': answer, 'summary': summary}
