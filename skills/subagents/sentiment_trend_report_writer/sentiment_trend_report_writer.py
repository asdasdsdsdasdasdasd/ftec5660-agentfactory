import json
import os
import re
from llm import call_llm
from tools import execute_shell_command


def _collect_context():
    ls = execute_shell_command('ls -1 *.json *.png *.md 2>/dev/null')
    files = [f.strip() for f in str(ls).splitlines() if f.strip()]
    context_parts = []
    for f in files:
        if f.endswith('.json'):
            raw = execute_shell_command('cat ' + f)
            context_parts.append('=== ' + f + ' ===\n' + str(raw)[:6000] + '\n')
        elif f.endswith('.png'):
            sz = execute_shell_command('stat -c %s ' + f).strip()
            context_parts.append('=== PLOT FILE: ' + f + ' (bytes=' + sz + ') ===')
    return files, '\n'.join(context_parts)


def main(query: str) -> dict:
    logic = []
    files, context = _collect_context()
    logic.append('Discovered files: ' + str(files))

    png_files = [f for f in files if f.endswith('.png')]
    chart_file = png_files[0] if png_files else 'chart.png'

    system_prompt = (
        'You are a professional research analyst and report writer. Write a complete, well-structured '
        'Markdown analysis report (900-1500 words) based STRICTLY on the evidence and data provided. '
        'Do NOT invent facts or numbers. The report MUST include these sections with proper Markdown headings:\n'
        '1. # Title\n'
        '2. ## Executive Summary\n'
        '3. ## Introduction and Background\n'
        '4. ## Data and Methodology\n'
        '5. ## Findings (report concrete quantitative data points found in the evidence, cite years and percentages where present)\n'
        '6. ## Discussion (a substantial section that critically interprets the findings, explains WHY sentiment changed, contrasts early vs recent periods, mentions drivers and nuances)\n'
        '7. ## Limitations\n'
        '8. ## Summary (a clear concluding summary of the overall trajectory)\n'
        'Reference the trend chart image with markdown syntax using the EXACT filename provided. '
        'Output ONLY the markdown content, no preamble.'
    )
    user_prompt = (
        'Task: ' + str(query) + '\n\n'
        'Trend chart image filename to reference: ' + chart_file + '\n\n'
        'Evidence and data files available:\n' + context
    )

    report = call_llm(system=system_prompt, messages=[{'role': 'user', 'content': user_prompt}], max_tokens=4000)

    r = str(report).strip()
    r = re.sub(r'^```(?:markdown|md)?', '', r).strip()
    r = re.sub(r'```$', '', r).strip()

    out_name = 'ev_sentiment_analysis_report.md'
    with open(out_name, 'w') as f:
        f.write(r)
    sz = os.path.getsize(out_name) if os.path.exists(out_name) else 0
    logic.append('Wrote ' + out_name + ' (' + str(sz) + ' bytes)')

    summary = call_llm(
        system='You are a report reviewer. Summarize what the report covers, its structure (list the section headings), and confirm the output files produced.',
        messages=[{'role': 'user', 'content': 'Log:\n' + '\n'.join(logic) + '\n\nReport (first 2500 chars):\n' + r[:2500]}],
        max_tokens=600,
    )

    return {
        'answer': 'Wrote ' + out_name + ' (' + str(sz) + ' bytes) referencing chart ' + chart_file + '. Files present: ' + str(files),
        'summary': summary,
    }
