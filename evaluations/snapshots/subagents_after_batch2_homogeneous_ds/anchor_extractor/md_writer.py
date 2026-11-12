from llm import call_llm
from tools import execute_shell_command
import json, re


def main(query: str) -> dict:
    # The query is expected to contain the data to write plus output filename instructions.
    plan_raw = call_llm(
        system=(
            'You are a markdown writer. The user provides content (possibly a list of items with topics and links) and asks to save it to a markdown file. '
            'Return ONLY JSON with keys: output_file (a .md filename), title (string), items (array of {topic, link}), notes (short string). '
            'Preserve the given order and exact URLs.'
        ),
        messages=[{'role': 'user', 'content': query}],
        max_tokens=2000,
    )
    try:
        m = re.search(r'\{.*\}', plan_raw, re.DOTALL)
        plan = json.loads(m.group(0)) if m else {}
    except Exception:
        plan = {}
    output_file = plan.get('output_file') or 'result.md'
    if not output_file.endswith('.md'):
        output_file += '.md'
    title = plan.get('title') or 'Results'
    items = plan.get('items') or []
    notes = plan.get('notes') or ''

    lines = ['# ' + title, '']
    if notes:
        lines.append(notes)
        lines.append('')
    lines.append('| # | Topic | Link |')
    lines.append('|---|-------|------|')
    for i, it in enumerate(items, 1):
        topic = str(it.get('topic', '')).replace('|', '/')
        link = str(it.get('link', ''))
        lines.append('| ' + str(i) + ' | ' + topic + ' | ' + link + ' |')
    lines.append('')
    lines.append('## Details')
    lines.append('')
    for i, it in enumerate(items, 1):
        topic = str(it.get('topic', ''))
        link = str(it.get('link', ''))
        if link:
            lines.append(str(i) + '. **' + topic + '** — [' + link + '](' + link + ')')
        else:
            lines.append(str(i) + '. **' + topic + '**')
    md_text = '\n'.join(lines)
    # write via python safely
    with open(output_file, 'w') as f:
        f.write(md_text)

    verify = execute_shell_command('ls -la ' + output_file + ' && echo --- && cat ' + output_file)

    summary = call_llm(
        system='Write a short SUMMARY of what markdown file was written and its content.',
        messages=[{'role': 'user', 'content': 'Query: ' + query + '\nFile written: ' + output_file + '\nContent:\n' + md_text}],
        max_tokens=800,
    )
    return {'answer': 'Wrote markdown to ' + output_file + ' with ' + str(len(items)) + ' items. Verify output: ' + verify[:800], 'summary': summary}
