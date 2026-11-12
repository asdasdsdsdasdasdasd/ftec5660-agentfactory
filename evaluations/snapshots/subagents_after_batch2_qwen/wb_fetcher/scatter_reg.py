import json
import re
import os
from llm import call_llm
from tools import execute_shell_command


NL = chr(10)
SCRIPT_TEMPLATE = (
    'import json@@import numpy as np@@import matplotlib@@matplotlib.use("Agg")@@import matplotlib.pyplot as plt@@@@'
    'with open("scatter_data.json") as f:@@    d = json.load(f)@@spec = d["spec"]@@pts = d["points"]@@'
    'xs = np.array([p["x"] for p in pts], dtype=float)@@ys = np.array([p["y"] for p in pts], dtype=float)@@'
    'labels = [p.get("label", "") for p in pts]@@@@'
    'fig, ax = plt.subplots(figsize=(11, 7))@@'
    'ax.scatter(xs, ys, s=70, color="#1f77b4", edgecolors="black", zorder=3, label="Data points")@@'
    'for x, y, lb in zip(xs, ys, labels):@@    if lb:@@        ax.annotate(str(lb), (x, y), textcoords="offset points", xytext=(5, 5), fontsize=7, color="#333")@@@@'
    'stats = {}@@stats["n"] = int(len(xs))@@'
    'if spec.get("fit_line", True) and len(xs) >= 2:@@'
    '    slope, intercept = np.polyfit(xs, ys, 1)@@'
    '    xs_line = np.linspace(xs.min(), xs.max(), 100)@@'
    '    ys_line = slope * xs_line + intercept@@'
    '    y_pred = slope * xs + intercept@@'
    '    ss_res = float(np.sum((ys - y_pred) ** 2))@@'
    '    ss_tot = float(np.sum((ys - ys.mean()) ** 2))@@'
    '    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0@@'
    '    r = float(np.corrcoef(xs, ys)[0, 1])@@'
    '    ax.plot(xs_line, ys_line, color="#d62728", linewidth=2.5, zorder=2, label="Regression line")@@'
    '    eq = "y = {:.6g}*x + {:.6g}".format(slope, intercept)@@'
    '    box = eq + chr(10) + "R^2 = {:.4f}".format(r2) + chr(10) + "r = {:.4f}".format(r) + chr(10) + "n = {}".format(len(xs))@@'
    '    ax.text(0.03, 0.97, box, transform=ax.transAxes, fontsize=10, va="top", ha="left",@@'
    '            bbox=dict(boxstyle="round", facecolor="white", alpha=0.85, edgecolor="gray"))@@'
    '    stats["slope"] = float(slope)@@    stats["intercept"] = float(intercept)@@    stats["r2"] = r2@@    stats["r"] = r@@@@'
    'ax.set_title(spec.get("title", "Scatter"), fontsize=14, fontweight="bold")@@'
    'ax.set_xlabel(spec.get("x_label", "X"), fontsize=11)@@'
    'ax.set_ylabel(spec.get("y_label", "Y"), fontsize=11)@@'
    'ax.grid(True, alpha=0.3)@@ax.legend(loc="lower right")@@fig.tight_layout()@@'
    'fig.savefig("scatter_regression.png", dpi=140)@@'
    'with open("fit_stats.json", "w") as f:@@    json.dump(stats, f, indent=2)@@'
    'print("SAVED scatter_regression.png with", len(xs), "points")@@print(json.dumps(stats))@@'
)


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


def main(query: str) -> dict:
    logic = []
    chk = execute_shell_command('python -c "import matplotlib, numpy; print(matplotlib.__version__)"')
    logic.append('check: ' + str(chk)[:200])
    if 'Error' in str(chk) or 'No module' in str(chk) or 'Traceback' in str(chk):
        execute_shell_command('pip install matplotlib numpy 2>&1 | tail -n 2')

    plan = call_llm(
        system=(
            "You are a data visualization planner. The user provides text containing a dataset "
            "of paired numeric observations (x and y values) plus a request to plot a scatter "
            "chart and fit a regression line. Extract a CLEAN dataset and chart spec. Return ONLY "
            "a JSON object with keys: title, x_label, y_label, points (list of objects each with "
            "numeric x, numeric y, and optional label for the year or id), and fit_line (boolean). "
            "Include ALL data pairs found. Do NOT invent data. Return ONLY valid JSON."
        ),
        messages=[{"role": "user", "content": "Request and data:\n" + str(query)}],
        max_tokens=3000,
    )
    spec = _parse_json(plan)
    if not isinstance(spec, dict) or not spec.get('points'):
        return {'answer': 'Failed to extract plottable data.', 'summary': 'LLM could not parse data: ' + str(plan)[:1000]}

    points = []
    for p in spec.get('points', []):
        if not isinstance(p, dict):
            continue
        try:
            x = float(str(p.get('x')).replace(',', ''))
            y = float(str(p.get('y')).replace(',', ''))
        except Exception:
            continue
        points.append({'x': x, 'y': y, 'label': str(p.get('label', ''))})
    if len(points) < 2:
        return {'answer': 'Not enough points: ' + str(len(points)), 'summary': 'spec=' + json.dumps(spec)[:500]}

    data = {'spec': {'title': spec.get('title', 'Scatter'), 'x_label': spec.get('x_label', 'X'),
                     'y_label': spec.get('y_label', 'Y'), 'fit_line': bool(spec.get('fit_line', True))},
            'points': points}
    execute_shell_command('mkdir -p charts 2>&1')
    with open('charts/scatter_data.json', 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logic.append('extracted ' + str(len(points)) + ' points')

    script = SCRIPT_TEMPLATE.replace('@@', NL)
    script = script.replace('fig.savefig("scatter_regression.png", dpi=140)', 'fig.savefig("../scatter_regression.png", dpi=140)')
    with open('charts/make_scatter.py', 'w') as f:
        f.write(script)
    out = execute_shell_command('cd charts && python make_scatter.py 2>&1')
    logic.append('run: ' + str(out).strip()[:600])
    exists = os.path.exists('scatter_regression.png')
    size = os.path.getsize('scatter_regression.png') if exists else 0

    stats = {}
    if os.path.exists('fit_stats.json'):
        try:
            stats = json.load(open('fit_stats.json'))
        except Exception:
            stats = {}

    summary = call_llm(
        system='You are a data visualization summarizer. Write a concise SUMMARY of how the scatter chart and regression were produced: data used, axis choices, fit statistics, files written.',
        messages=[{'role': 'user', 'content': 'Request: ' + str(query) + '\nSpec: ' + json.dumps(data['spec']) + '\nPoints: ' + str(len(points)) + '\nStats: ' + json.dumps(stats) + '\nLog:\n' + '\n'.join(logic)}],
        max_tokens=1200,
    )
    if exists:
        answer = ('Created scatter_regression.png (' + str(size) + ' bytes) with ' + str(len(points)) +
                  ' points. Fit: slope=' + str(round(stats.get('slope', 0), 8)) + ' intercept=' + str(round(stats.get('intercept', 0), 4)) +
                  ' R2=' + str(round(stats.get('r2', 0), 4)) + ' r=' + str(round(stats.get('r', 0), 4)) +
                  '. Files: scatter_data.json, make_scatter.py, fit_stats.json, scatter_regression.png.')
    else:
        answer = 'FAILED to create scatter_regression.png. ' + ' | '.join(logic[-3:])
    return {'answer': answer, 'summary': summary}
