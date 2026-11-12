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

    chk = execute_shell_command('python -c "import matplotlib; print(matplotlib.__version__)"')
    logic.append('matplotlib check: ' + str(chk).strip()[:200])
    if 'Error' in str(chk) or 'No module' in str(chk) or 'Traceback' in str(chk):
        inst = execute_shell_command('pip install matplotlib 2>&1 | tail -n 3')
        logic.append('install matplotlib: ' + str(inst)[:200])

    plan = call_llm(
        system=(
            "You are a data visualization planner. The user provides text containing "
            "numeric data over time (or some ordered dimension) plus what chart they want. "
            "Extract a CLEAN dataset and a chart spec. Return ONLY a JSON object with keys: "
            "'title' (plain text, no emojis), 'x_label', 'y_label', 'chart_type' (one of line/bar/scatter), "
            "and 'points' a list of objects each with 'x' (numeric ordering value), optional "
            "'x_label_override' (human-readable label), 'y' (numeric value), optional 'series'. "
            "Include ALL data points found. Convert units consistently. Do NOT invent data. Return ONLY valid JSON."
        ),
        messages=[{'role': 'user', 'content': 'Request and data:\n' + str(query)}],
        max_tokens=3000,
    )
    spec = _parse_json(plan)
    if not isinstance(spec, dict) or not spec.get('points'):
        plan = call_llm(
            system=("Extract every numeric data point from the text into JSON: "
                "{'title':str,'x_label':str,'y_label':str,'chart_type':str,'points':[{'x_label_override':str,'y':number}]}. Return ONLY JSON."),
            messages=[{'role': 'user', 'content': str(query)}],
            max_tokens=3000,
        )
        spec = _parse_json(plan)
    if not isinstance(spec, dict) or not spec.get('points'):
        return {'answer': 'Failed to extract plottable data.',
                'summary': 'LLM could not parse numeric data. Raw: ' + str(plan)[:1000]}

    points = []
    for i, p in enumerate(spec.get('points', [])):
        if not isinstance(p, dict):
            continue
        try:
            y = float(p.get('y'))
        except Exception:
            continue
        xraw = p.get('x', None)
        try:
            x = float(xraw)
        except Exception:
            lbl = str(p.get('x_label_override', p.get('label', i)))
            nums = re.findall(r'-?\d+(?:\.\d+)?', lbl)
            x = float(nums[0]) if nums else float(i)
        points.append({'x': x, 'y': y, 'label': str(p.get('x_label_override', p.get('label', ''))), 'series': str(p.get('series', 'default'))})

    if not points:
        return {'answer': 'No numeric points after normalization.',
                'summary': 'Spec: ' + json.dumps(spec)[:800]}

    points.sort(key=lambda d: d['x'])
    data = {'spec': {'title': spec.get('title', 'Chart'), 'x_label': spec.get('x_label', 'X'),
                     'y_label': spec.get('y_label', 'Y'), 'chart_type': spec.get('chart_type', 'line')},
            'points': points}
    with open('plot_data.json', 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logic.append('Extracted ' + str(len(points)) + ' points; chart_type=' + str(data['spec']['chart_type']))

    script = """
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
"""
    with open('make_chart.py', 'w') as f:
        f.write(script)

    out = execute_shell_command('python make_chart.py 2>&1')
    logic.append('Run make_chart: ' + str(out).strip()[:400])
    if not os.path.exists('population_chart.png'):
        fb = """
import json, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
d=json.load(open('plot_data.json'))
pts=d['points']
xs=[p['x'] for p in pts]; ys=[p['y'] for p in pts]
fig,ax=plt.subplots(figsize=(14,8))
ax.plot(xs,ys,marker='o')
ax.set_title(d['spec'].get('title','Chart'))
ax.set_xlabel(d['spec'].get('x_label','X'))
ax.set_ylabel(d['spec'].get('y_label','Y'))
ax.grid(True,alpha=0.3)
fig.tight_layout()
fig.savefig('population_chart.png',dpi=130)
print('fallback saved')
"""
        with open('make_chart_fb.py', 'w') as f:
            f.write(fb)
        out2 = execute_shell_command('python make_chart_fb.py 2>&1')
        logic.append('Fallback run: ' + str(out2).strip()[:400])

    exists = os.path.exists('population_chart.png')
    size = os.path.getsize('population_chart.png') if exists else 0
    logic.append('Output exists=' + str(exists) + ' size=' + str(size))

    summary = call_llm(
        system='You are a data visualization summarizer. Write a concise SUMMARY of how the chart was produced: data extracted, axis choices, files written. 100-400 words.',
        messages=[{'role': 'user', 'content': 'Request: ' + str(query) + '\n\nSpec used: ' + json.dumps(data['spec']) + '\nPoints: ' + str(len(points)) + '\nLog:\n' + '\n'.join(logic)}],
        max_tokens=1200,
    )

    if exists:
        answer = 'Created population_chart.png (' + str(size) + ' bytes) with ' + str(len(points)) + ' data points using chart_type=' + str(data['spec']['chart_type']) + '. Files: plot_data.json, make_chart.py, population_chart.png.'
    else:
        answer = 'FAILED to generate population_chart.png. ' + ' | '.join(logic[-3:])

    return {'answer': answer, 'summary': summary}
