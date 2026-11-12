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

    # Ensure matplotlib
    chk = execute_shell_command('python -c "import matplotlib; print(matplotlib.__version__)"')
    logic.append('matplotlib: ' + str(chk).strip()[:120])
    if 'Error' in str(chk) or 'No module' in str(chk) or 'Traceback' in str(chk):
        execute_shell_command('pip install matplotlib 2>&1 | tail -n 2')

    # Step 1: LLM decides which JSON file and fields to read, plus chart title/axes.
    plan_prompt = (
        'You are a data-viz planner. The user wants a labeled bar chart of keyword frequencies.\n'
        f'User request: {query}\n\n'
        'List the .json files present and decide which one holds rows of {keyword, count}. '
        'Return ONLY JSON: {"file": "name.json", "keyword_field": "keyword", "count_field": "count", "title": "...", "x_label": "...", "y_label": "...", "top_n": 20, "orientation": "horizontal"}\n'
        'If the file is unclear, pick the most likely one containing a list under key items or a top-level list of {keyword,count}.'
    )
    files = execute_shell_command('ls -1 *.json 2>/dev/null')
    plan_raw = call_llm(
        system='You output only valid JSON.',
        messages=[{'role': 'user', 'content': 'JSON files present:\n' + files + '\n\n' + plan_prompt}],
        max_tokens=600,
    )
    plan = _parse_json(plan_raw) or {}
    logic.append('plan: ' + json.dumps(plan)[:400])

    data_file = plan.get('file') or 'trending_keywords.json'
    kf = plan.get('keyword_field') or 'keyword'
    cf = plan.get('count_field') or 'count'
    title = plan.get('title') or 'Top Trending Keywords'
    x_label = plan.get('x_label') or 'Keyword'
    y_label = plan.get('y_label') or 'Frequency'
    top_n = int(plan.get('top_n') or 20)
    horizontal = (plan.get('orientation', 'horizontal') != 'vertical')

    # Step 2: Load rows robustly
    rows = []
    try:
        with open(data_file, 'r', encoding='utf-8', errors='replace') as f:
            raw = json.load(f)
        if isinstance(raw, dict) and 'items' in raw:
            raw = raw['items']
        if isinstance(raw, list):
            for it in raw:
                if not isinstance(it, dict):
                    continue
                kw = str(it.get(kf, it.get('keyword', it.get('name', '')))).strip()
                try:
                    ct = float(it.get(cf, it.get('count', it.get('uses', it.get('value', 0)))))
                except Exception:
                    continue
                if kw:
                    rows.append({'keyword': kw, 'count': ct})
    except Exception as e:
        logic.append('load error: ' + str(e))

    if not rows:
        return {'answer': 'No data rows could be loaded from ' + str(data_file), 'summary': '\n'.join(logic)}

    # Dedup by lowercased keyword, sort desc, take top_n
    agg = {}
    for r in rows:
        k = r['keyword'].lower()
        agg[k] = max(agg.get(k, 0.0), r['count'])
    items = sorted([{'keyword': k, 'count': v} for k, v in agg.items()], key=lambda d: d['count'], reverse=True)[:top_n]
    logic.append('plotting ' + str(len(items)) + ' items')

    with open('chart_items.json', 'w', encoding='utf-8') as f:
        json.dump({'title': title, 'x_label': x_label, 'y_label': y_label, 'horizontal': horizontal, 'items': items}, f, ensure_ascii=False, indent=2)

    script = r'''
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
'''
    with open('make_bar_chart.py', 'w', encoding='utf-8') as f:
        f.write(script)

    out = execute_shell_command('python make_bar_chart.py 2>&1')
    logic.append('run: ' + str(out).strip()[:500])

    out_name = 'trending_keywords_bar_chart.png'
    exists = os.path.exists(out_name)
    size = os.path.getsize(out_name) if exists else 0

    summary = call_llm(
        system='You are a data visualization summarizer. Write a concise SUMMARY (100-400 words) of how the bar chart was produced: data source file, number of bars, ordering, axis labels, output file.',
        messages=[{'role': 'user', 'content': 'Request: ' + query + '\nFile: ' + data_file + '\nItems: ' + str(len(items)) + '\nOutput exists: ' + str(exists) + ' size: ' + str(size) + '\nLog:\n' + '\n'.join(logic)}],
        max_tokens=1000,
    )

    if exists:
        answer = 'Created ' + out_name + ' (' + str(size) + ' bytes) with ' + str(len(items)) + ' bars. Files: chart_items.json, make_bar_chart.py, ' + out_name + '.'
    else:
        answer = 'FAILED to create bar chart. ' + ' | '.join(logic[-3:])
    return {'answer': answer, 'summary': summary}
