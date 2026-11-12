import json
import os
import re
import subprocess
from llm import call_llm
from tools import execute_shell_command


def _parse_json(text):
    if text is None:
        return None
    t = str(text).strip()
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


def _load_series(path):
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        data = json.load(f)
    series = []
    # Support common shapes: {series:[{name,unit,values:{year:val}}]}
    raw = data.get('series', []) if isinstance(data, dict) else []
    for s in raw:
        if not isinstance(s, dict):
            continue
        name = s.get('name', 'series')
        unit = s.get('unit', '')
        values = s.get('values', {}) or {}
        pts = []
        for yr, val in values.items():
            try:
                y = int(str(yr).strip())
                v = float(str(val).replace(',', '').strip())
            except Exception:
                continue
            pts.append((y, v))
        pts.sort()
        if pts:
            series.append({'name': name, 'unit': unit, 'points': pts})
    return data, series


def main(query: str) -> dict:
    logic = []
    # Step 1: find JSON files
    ls = execute_shell_command('ls -1 *.json 2>/dev/null')
    files = [x.strip() for x in ls.splitlines() if x.strip()]
    logic.append('json files: ' + str(files))
    if not files:
        return {'answer': 'No JSON data files found to plot.', 'summary': 'No .json files in workspace.'}

    # Step 2: LLM picks which file to plot
    pick = call_llm(
        system="You choose the best JSON file to plot from a list. Return ONLY JSON {\"file\": \"name\"}.",
        messages=[{'role': 'user', 'content': f'Query: {query}\nAvailable JSON files: {files}'}],
        max_tokens=200,
    )
    pj = _parse_json(pick) or {}
    chosen = pj.get('file')
    if chosen not in files:
        # prefer one with 'series' key
        chosen = None
        for fn in files:
            try:
                d = json.load(open(fn))
                if isinstance(d, dict) and 'series' in d:
                    chosen = fn
                    break
            except Exception:
                continue
        chosen = chosen or files[0]
    logic.append('chosen file: ' + str(chosen))

    try:
        data, series = _load_series(chosen)
    except Exception as e:
        return {'answer': f'Failed to load/parse {chosen}: {e}', 'summary': 'Error loading JSON: ' + str(e)}
    if not series:
        return {'answer': f'No plottable series found in {chosen}.', 'summary': 'File loaded but no year->value series found. Content preview: ' + str(data)[:500]}

    # Step 3: LLM produces chart spec
    desc = []
    for s in series:
        desc.append({'name': s['name'], 'unit': s['unit'], 'n': len(s['points']), 'first': s['points'][0], 'last': s['points'][-1]})
    spec_resp = call_llm(
        system=(
            "You are a chart designer. Given a plotting request and series metadata, return ONLY a JSON object with: "
            "title (string), xlabel (string), ylabel (string), chart_type ('line' or 'bar'), "
            "y_scale ('linear' or 'log'), scale_factor (number to divide y values by for readability, e.g. 1000000 for millions, or 1 for none), "
            "and y_unit_note (string describing resulting unit). No emojis."
        ),
        messages=[{'role': 'user', 'content': f'Plot request: {query}\nSeries metadata: {json.dumps(desc, ensure_ascii=False)}'}],
        max_tokens=500,
    )
    spec = _parse_json(spec_resp) or {}
    title = spec.get('title') or (' '.join([s['name'] for s in series]))
    xlabel = spec.get('xlabel') or 'Year'
    ylabel = spec.get('ylabel') or 'Value'
    chart_type = spec.get('chart_type') or 'line'
    y_scale = spec.get('y_scale') or 'linear'
    try:
        scale_factor = float(spec.get('scale_factor') or 1)
    except Exception:
        scale_factor = 1.0
    if scale_factor == 0:
        scale_factor = 1.0
    logic.append('spec: ' + json.dumps(spec, ensure_ascii=False)[:300])

    # Save plot spec + data for the plotting script
    plot_payload = {'series': series, 'spec': {'title': title, 'xlabel': xlabel, 'ylabel': ylabel, 'chart_type': chart_type, 'y_scale': y_scale, 'scale_factor': scale_factor}}
    with open('plot_payload.json', 'w') as f:
        json.dump(plot_payload, f, ensure_ascii=False)

    # Step 4: write standalone matplotlib script
    script = r'''
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
'''
    with open('make_chart.py', 'w') as f:
        f.write(script)

    # Step 5: ensure matplotlib and run
    execute_shell_command('python -c "import matplotlib" 2>/dev/null || pip install matplotlib 2>&1 | tail -1')
    run_out = execute_shell_command('python make_chart.py 2>&1')
    logic.append('run output: ' + str(run_out)[:400])

    # Step 6: verify PNG
    check = execute_shell_command("ls -la population_chart.png 2>&1")
    logic.append('check: ' + str(check)[:300])
    ok = 'population_chart.png' in str(check) and 'No such' not in str(check)

    data_desc = '; '.join([f"{s['name']}: {len(s['points'])} pts {s['points'][0][0]}-{s['points'][-1][0]}" for s in series])
    status_txt = 'Success.' if ok else ('Run output: ' + str(run_out)[:300])
    answer = 'Plotted ' + data_desc + ' from ' + chosen + '. Chart saved to population_chart.png. ' + status_txt

    summary = call_llm(
        system='You are a data visualization summarizer. Write a detailed SUMMARY (100-2000 words) of how the chart was produced: file chosen, series used, chart spec, and verification.',
        messages=[{'role': 'user', 'content': f'Query: {query}\nSteps:\n' + '\n'.join(logic) + f'\nFinal chart ok: {ok}\nData: {data_desc}\nWrite the SUMMARY.'}],
        max_tokens=1500,
    )
    return {'answer': answer, 'summary': summary}
