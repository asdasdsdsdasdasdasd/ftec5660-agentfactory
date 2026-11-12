import json, os
from llm import call_llm
from tools import execute_shell_command


def main(query):
    # Discover data file: look for a trending JSON in workspace
    out = execute_shell_command("ls -1 *.json 2>/dev/null")
    files = [f.strip() for f in out.splitlines() if f.strip().endswith('.json')]
    data_file = None
    for f in files:
        try:
            d = json.load(open(f, encoding='utf-8'))
        except Exception:
            continue
        if isinstance(d, dict) and 'items' in d and isinstance(d['items'], list) and d['items']:
            data_file = f
            break
    if not data_file:
        return {'answer': 'No trending data JSON with an items list found.', 'summary': f'Files seen: {files}'}

    d = json.load(open(data_file, encoding='utf-8'))
    items = d['items'][:20]
    titles = [str(it.get('title','')) for it in items]
    heats = [it.get('heat', 0) for it in items]

    # Use LLM to produce a clean chart title
    try:
        chart_title = call_llm(system='Return ONLY a short chart title (no quotes) for a bar chart of trending topics, in Chinese.', messages=[{'role':'user','content': f'Source: {d.get("source")}. Query: {query}'}]).strip().strip('"')
    except Exception:
        chart_title = 'Trending Topics Top 20'

    def pyrepr(s):
        return json.dumps(s, ensure_ascii=False)

    script = f'''
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import matplotlib.font_manager as fm

# try to find a CJK-capable font, else fallback
titles = {json.dumps(titles, ensure_ascii=False)}
heats = {json.dumps(heats, ensure_ascii=False)}
title = {json.dumps(chart_title, ensure_ascii=False)}

cjk_candidates = ['Noto Sans CJK SC','Noto Sans CJK JP','WenQuanYi Zen Hei','WenQuanYi Micro Hei','SimHei','Microsoft YaHei','Arial Unicode MS','Source Han Sans','Droid Sans Fallback']
avail = {{f.name for f in fm.fontManager.ttflist}}
chosen = None
for c in cjk_candidates:
    if c in avail:
        chosen = c; break
if chosen:
    plt.rcParams['font.sans-serif'] = [chosen]
plt.rcParams['axes.unicode_minus'] = False

# reverse so top item is at top of horizontal bar
rev_titles = titles[::-1]
rev_heats = heats[::-1]
fig, ax = plt.subplots(figsize=(12, 10))
bars = ax.barh(range(len(rev_titles)), rev_heats, color='#e74c3c')
ax.set_yticks(range(len(rev_titles)))
lbl = [ (t[:28] + '…') if len(t) > 28 else t for t in rev_titles ]
ax.set_yticklabels(lbl, fontsize=9)
ax.set_xlabel('Heat / 热度', fontsize=11)
ax.set_title(title, fontsize=15, fontweight='bold')
for b, h in zip(bars, rev_heats):
    ax.text(b.get_width(), b.get_y()+b.get_height()/2, f' {{h:,.0f}}', va='center', fontsize=8)
plt.tight_layout()
plt.savefig('trending_top20.png', dpi=150)
print('SAVED trending_top20.png')
'''
    with open('plot_trending.py','w',encoding='utf-8') as f:
        f.write(script)

    # ensure matplotlib present
    res = execute_shell_command("python3 -c 'import matplotlib' 2>&1 || pip install matplotlib -q 2>&1 | tail -1")
    run1 = execute_shell_command('python3 plot_trending.py 2>&1')
    evidence = [f'Data file: {data_file}', f'items: {len(items)}', f'mpl check: {res[:120]}', f'run1: {run1[-500:]}']

    if not os.path.exists('trending_top20.png'):
        # fallback: install a CJK font then retry, or drop CJK
        execute_shell_command("pip install -q matplotlib 2>&1 | tail -1")
        run2 = execute_shell_command('python3 plot_trending.py 2>&1')
        evidence.append(f'run2: {run2[-800:]}')

    exists = os.path.exists('trending_top20.png')
    size = os.path.getsize('trending_top20.png') if exists else 0
    summary = call_llm(system='Write a detailed SUMMARY of creating a bar chart from trending JSON data.', messages=[{'role':'user','content': f'Query: {query}\nEvidence:\n' + '\n'.join(evidence) + f'\nChart exists: {exists}, size: {size}\nWrote trending_top20.png. Write 100-400 words on process and result.'}])
    if exists:
        return {'answer': f'Created bar chart trending_top20.png ({size} bytes) of top {len(items)} trending topics from {d.get("source")}.', 'summary': summary}
    else:
        return {'answer': 'FAILED to create chart.', 'summary': summary + '\n' + '\n'.join(evidence)}
