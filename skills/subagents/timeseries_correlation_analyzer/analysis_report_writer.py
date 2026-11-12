import json
import os
from llm import call_llm
from tools import execute_shell_command


def main(query: str) -> dict:
    logic = []
    # Gather any analysis/result json files present
    ls = execute_shell_command('ls *.json 2>&1')
    logic.append('Files: ' + str(ls)[:500])
    evidence = ''
    for fname in ['analysis_results.json', 'fetched_data.json']:
        if os.path.exists(fname):
            sz = os.path.getsize(fname)
            content = ''
            if fname == 'analysis_results.json':
                content = execute_shell_command('cat analysis_results.json')
            elif fname == 'fetched_data.json':
                # only a sample
                content = execute_shell_command('python -c "import json;d=json.load(open(\'fetched_data.json\'));print(\"COUNTRY COUNT:\",len(set(r[\"country\"] for r in d[\"rows\"])));print(\"ROWS:\",len(d[\"rows\"]));print(\"YEAR RANGE:\",min(r[\"year\"] for r in d[\"rows\"]),\"-\",max(r[\"year\"] for r in d[\"rows\"]))"')
            evidence += '\n=== %s (%d bytes) ===\n%s\n' % (fname, sz, str(content)[:3000])
    plots = execute_shell_command('ls *.png 2>&1')
    logic.append('Plots: ' + str(plots)[:300])

    report = call_llm(
        system=('You are a professional environmental data report writer. Write a complete, well-structured Markdown report (600-1200 words) that: '
                '1) States the data source (Our World in Data) and countries/years covered, 2) Presents the methodology (Pearson correlation, per-country trends), '
                '3) Reports the quantitative findings including pooled r/R2 and per-country within-country correlations and % changes, '
                '4) Interprets the results (decoupling vs coupled growth), 5) Includes a Limitations section, and 6) Concludes. '
                'Reference the generated plot files trends_plot.png and correlation_scatter.png. Use proper headings and bullet points. Output ONLY the markdown content.'),
        messages=[{'role': 'user', 'content': 'Task: ' + str(query) + '\n\nEvidence available:\n' + evidence + '\n\nPlot files present:\n' + str(plots)}],
        max_tokens=2500,
    )
    with open('analysis_report.md', 'w') as f:
        f.write(str(report))
    sz = os.path.getsize('analysis_report.md') if os.path.exists('analysis_report.md') else 0
    logic.append('Wrote analysis_report.md (%d bytes)' % sz)

    summary = call_llm(
        system='Summarize what the report contains and confirm which files were produced.',
        messages=[{'role': 'user', 'content': 'Log:\n' + '\n'.join(logic)}],
        max_tokens=400,
    )
    return {'answer': 'Wrote analysis_report.md (%d bytes). Plot files: %s' % (sz, str(plots).strip()), 'summary': summary}
