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


def _find_series_values(obj):
    candidates = []

    def walk(o, path):
        if isinstance(o, dict):
            year_like = [k for k in o.keys() if re.fullmatch(r'\d{4}', str(k))]
            if len(year_like) >= 3:
                vals = {}
                for k in year_like:
                    try:
                        vals[int(k)] = float(str(o[k]).replace(',', ''))
                    except Exception:
                        pass
                if len(vals) >= 3:
                    candidates.append((path, vals))
            for k, v in o.items():
                walk(v, path + '/' + str(k))
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, path + '/[' + str(i) + ']')

    walk(obj, '')
    if not candidates:
        return None, None
    candidates.sort(key=lambda c: len(c[1]), reverse=True)
    return candidates[0][1], candidates[0][0]


def main(query: str) -> dict:
    logic = []

    chk = execute_shell_command('python -c "import matplotlib; print(matplotlib.__version__)"')
    logic.append('matplotlib check: ' + str(chk).strip()[:150])
    if 'Error' in str(chk) or 'No module' in str(chk) or 'Traceback' in str(chk):
        inst = execute_shell_command('pip install matplotlib 2>&1 | tail -n 2')
        logic.append('install: ' + str(inst)[:150])

    plan = call_llm(
        system=(
            "You are a data visualization planner. A JSON file containing a numeric "
            "year->value time series exists in the workspace (commonly series_data.json). "
            "Based on the user's request, return ONLY a JSON object with keys: "
            "'file' (the json filename), 'title', 'x_label', 'y_label', 'chart_type' "
            "(line/bar/scatter). Return ONLY valid JSON."
        ),
        messages=[{'role': 'user', 'content': 'Request: ' + str(query)}],
        max_tokens=600,
    )
    spec = _parse_json(plan) or {}
    fname = spec.get('file') or 'series_data.json'

    if not os.path.exists(fname):
        jsons = [f for f in os.listdir('.') if f.endswith('.json')]
        logic.append('specified file missing; json files: ' + str(jsons))
        for j in jsons:
            try:
                obj = json.load(open(j))
            except Exception:
                continue
            vals, path = _find_series_values(obj)
            if vals:
                fname = j
                break

    try:
        obj = json.load(open(fname))
    except Exception as e:
        return {'answer': 'Could not read JSON file: ' + str(e), 'summary': '\n'.join(logic)}

    vals, path = _find_series_values(obj)
    if not vals:
        return {'answer': 'No numeric year->value series found in ' + fname, 'summary': '\n'.join(logic)}
    logic.append('Using file=' + fname + ' series_path=' + str(path) + ' points=' + str(len(vals)))

    years = sorted(vals.keys())
    ys = [vals[y] for y in years]

    title = spec.get('title', 'Time Series')
    x_label = spec.get('x_label', 'Year')
    y_label = spec.get('y_label', 'Value')
    ct = spec.get('chart_type', 'line')

    plot_data = {'spec': {'title': title, 'x_label': x_label, 'y_label': y_label, 'chart_type': ct},
                 'years': years, 'values': ys}
    json.dump(plot_data, open('plot_data.json', 'w'), indent=2, ensure_ascii=False)

    script = '''
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

d = json.load(open("plot_data.json"))
spec = d["spec"]
years = d["years"]
ys = d["values"]
ct = spec.get("chart_type", "line")

fig, ax = plt.subplots(figsize=(14, 8))
if ct == "bar":
    ax.bar([str(y) for y in years], ys, color="steelblue")
    plt.xticks(rotation=90)
elif ct == "scatter":
    ax.scatter(years, ys, color="steelblue")
else:
    ax.plot(years, ys, marker="o", linewidth=2, markersize=4, color="steelblue")

if ys:
    max_i = max(range(len(ys)), key=lambda i: ys[i])
    ax.annotate("Peak: %s (%.2f)" % (years[max_i], ys[max_i]),
                xy=(years[max_i], ys[max_i]),
                xytext=(10, 10), textcoords="offset points",
                fontsize=11, color="red",
                arrowprops=dict(arrowstyle="->", color="red"))

ax.set_title(spec.get("title", "Time Series"), fontsize=16, fontweight="bold")
ax.set_xlabel(spec.get("x_label", "Year"), fontsize=13)
ax.set_ylabel(spec.get("y_label", "Value"), fontsize=13)
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig("population_chart.png", dpi=130)
print("SAVED population_chart.png with", len(years), "points")
'''
    with open('make_chart.py', 'w') as f:
        f.write(script)

    out = execute_shell_command('python make_chart.py 2>&1')
    logic.append('Run make_chart: ' + str(out).strip()[:400])

    exists = os.path.exists('population_chart.png')
    size = os.path.getsize('population_chart.png') if exists else 0
    logic.append('Output exists=' + str(exists) + ' size=' + str(size))

    summary = call_llm(
        system='You are a data visualization summarizer. Write a concise SUMMARY (100-400 words) of how the chart was produced: data source file, number of points, axis choices, files written, and whether the PNG was created successfully.',
        messages=[{'role': 'user', 'content': 'Request: ' + str(query) + '\nFile: ' + fname + '\nPoints: ' + str(len(years)) + '\nLog:\n' + '\n'.join(logic)}],
        max_tokens=1000,
    )

    if exists and ys:
        peak_i = max(range(len(ys)), key=lambda i: ys[i])
        answer = 'Created population_chart.png (' + str(size) + ' bytes) with ' + str(len(years)) + ' data points from ' + fname + '. Peak year: ' + str(years[peak_i]) + '. Files: plot_data.json, make_chart.py, population_chart.png.'
    else:
        answer = 'FAILED to generate chart. ' + ' | '.join(logic[-3:])

    return {'answer': answer, 'summary': summary}
