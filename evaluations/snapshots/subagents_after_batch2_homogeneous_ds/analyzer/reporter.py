import json
import re
import os
from llm import call_llm
from tools import execute_shell_command


def main(query: str) -> dict:
    """Generic report + chart generator for sentiment-over-time analyses.
    Reads sentiment_timeline.json (produced by the analyzer) and optionally
    evidence.json. Generates a trend chart (png) and a markdown report with
    Introduction, Methodology, Trend Analysis, Discussion, and Summary sections.
    """
    # Step 1: parse request for file names and output naming
    plan = call_llm(
        system=("Parse this request. Return JSON with keys: 'timeline_file' (default "
                "'sentiment_timeline.json'), 'evidence_file' (default 'evidence.json'), "
                "'chart_file' (default 'sentiment_trend.png'), 'report_file' (default "
                "'report.md'), 'title' (a concise report title), and 'metric' (which "
                "quantity to chart, e.g. 'net_sentiment'). Return ONLY valid JSON."),
        messages=[{"role": "user", "content": query}],
        max_tokens=400,
    )
    try:
        plan_json = json.loads(re.search(r"\{.*\}", plan, re.DOTALL).group(0))
    except Exception:
        plan_json = {}
    timeline_file = plan_json.get("timeline_file", "sentiment_timeline.json")
    evidence_file = plan_json.get("evidence_file", "evidence.json")
    chart_file = plan_json.get("chart_file", "sentiment_trend.png")
    report_file = plan_json.get("report_file", "report.md")
    title = plan_json.get("title", "Public Sentiment Trend Analysis")

    try:
        with open(timeline_file) as f:
            tl = json.load(f)
    except Exception as e:
        return {"answer": f"Could not read {timeline_file}: {e}", "summary": "Failed to load timeline file."}

    timeline = tl.get("timeline", [])
    focus = tl.get("focus", "")
    # Only chart periods that have data and are not 'Unknown' (keep Unknown as annotation)
    plot_rows = [t for t in timeline if t.get("total", 0) > 0 and t.get("period") != "Unknown"]
    unknown_row = next((t for t in timeline if t.get("period") == "Unknown" and t.get("total", 0) > 0), None)
    if not plot_rows:
        plot_rows = [t for t in timeline if t.get("total", 0) > 0]

    # Load evidence for discussion context
    evidence_items = []
    topic_summary_text = ""
    try:
        with open(evidence_file) as f:
            ev = json.load(f)
        evidence_items = ev.get("evidence", [])[:40]
        topic_summary_text = ev.get("topic_summary", "")
    except Exception:
        pass

    # Step 2: Generate chart via matplotlib in a subprocess (execute_shell_command)
    chart_data = json.dumps([
        {"period": r["period"], "net": r.get("net_sentiment", 0),
         "total": r.get("total", 0), "pos": r.get("positive", 0),
         "neg": r.get("negative", 0), "neu": r.get("neutral", 0)}
        for r in plot_rows
    ])
    py = r'''
import json, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

rows = json.loads(CHARTPAYLOAD)
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
ax1.set_title(CHARTTITLE)
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
plt.savefig(CHARTFILE, dpi=130)
print('chart saved')
'''
    py = py.replace("CHARTPAYLOAD", repr(chart_data)).replace("CHARTFILE", repr(chart_file)).replace("CHARTTITLE", repr(title))
    # write python script and run it
    with open("_plot_chart.py", "w") as f:
        f.write(py)
    out = execute_shell_command("python _plot_chart.py 2>&1")

    # Step 3: Generate the report text with an LLM
    timeline_str = json.dumps(timeline, ensure_ascii=False, indent=2)
    ev_sample = "\n".join(f"- [{e.get('date_hint','')}] {str(e.get('text',''))[:200]}" for e in evidence_items)

    report_body = call_llm(
        system=(
            "You are an analyst writing a markdown report on how public sentiment "
            "about a topic changed over time. Use the provided sentiment timeline "
            "and evidence samples. Write a well-structured report with EXACTLY these "
            "sections in order: '# <Title>', '## Introduction', '## Methodology', "
            "'## Trend Analysis', and '## Discussion'. In Trend Analysis, describe "
            "the numeric net-sentiment trajectory across periods and cite the "
            "numbers. In Discussion, interpret WHY sentiment changed, cite specific "
            "evidence/quotes, note the key debate and competing perspectives, and acknowledge "
            "limitations and the 'Unknown' undated share. Do NOT write a Summary "
            "section (it is appended separately). Reference the accompanying chart. "
            "Use professional, objective tone. Plain markdown only."
        ),
        messages=[{"role": "user", "content": f"Report title: {title}\nResearch focus: {focus}\n\nSentiment timeline (JSON):\n{timeline_str}\n\nEvidence samples:\n{ev_sample}\n\nDocument overview:\n{topic_summary_text[:1500]}\n\nWrite the report body (Introduction through Discussion, no Summary)."}],
        max_tokens=4000,
    )

    summary_section = call_llm(
        system=(
            "Write a '## Summary' markdown section (150-250 words) giving the "
            "bottom-line on how public sentiment changed over time, the key numeric "
            "findings, and the overall takeaway. Start with the exact header '## Summary'. "
            "Plain markdown only, no other sections."
        ),
        messages=[{"role": "user", "content": f"Topic: {title}\nFocus: {focus}\nTimeline: {timeline_str}\n\nWrite the Summary section now."}],
        max_tokens=700,
    )
    if "## Summary" not in summary_section:
        summary_section = "## Summary\n\n" + summary_section.strip()
    body_no_summary = re.split(r"\n##\s*Summary", report_body)[0].rstrip()
    report_body = body_no_summary + "\n\n" + summary_section.strip() + "\n"

    # Prepend chart image reference if chart made
    chart_note = f"\n\n![Sentiment trend chart]({chart_file})\n" if os.path.exists(chart_file) else "\n\n(Chart generation failed.)\n"
    # Insert chart right after the first heading line
    lines = report_body.split("\n")
    if lines and lines[0].startswith("#"):
        full_report = lines[0] + chart_note + "\n" + "\n".join(lines[1:])
    else:
        full_report = f"# {title}" + chart_note + "\n" + report_body

    with open(report_file, "w") as f:
        f.write(full_report)

    summary = call_llm(
        system="Summarize what was produced. Write 150-500 words describing the chart generated, the report file, and the key sentiment findings.",
        messages=[{"role": "user", "content": f"Chart file: {chart_file} (exists={os.path.exists(chart_file)}), plot output: {out}\nReport file: {report_file}\nTimeline: {timeline_str}\n\nWrite summary."}],
        max_tokens=1000,
    )

    return {
        "answer": f"Generated chart '{chart_file}' and report '{report_file}'.",
        "summary": summary,
    }
