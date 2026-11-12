import json
import re
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
    m = re.search(r'\{.*\}', t, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


def main(query: str) -> dict:
    # The query contains the report content/instructions and desired filename.
    # Ask the LLM to produce the FULL markdown document verbatim as JSON.
    plan_raw = call_llm(
        system=(
            'You are a technical report writer. The user provides report content, findings, '
            'and a desired filename. Produce a complete, clean, well-formatted Markdown '
            'document that faithfully includes ALL the information provided (tables, numbers, '
            'interpretation, limitations). Return ONLY a JSON object with keys: '
            'output_file (a .md filename), and markdown (the FULL markdown document as a '
            'single string using real newline characters). Do not omit any provided facts or '
            'numbers. Return ONLY valid JSON.'
        ),
        messages=[{'role': 'user', 'content': query}],
        max_tokens=4000,
    )
    plan = _parse_json(plan_raw) or {}
    output_file = plan.get('output_file') or 'report.md'
    if not output_file.endswith('.md'):
        output_file += '.md'
    markdown = plan.get('markdown') or ''
    if not markdown.strip():
        return {'answer': 'Failed to generate markdown content.', 'summary': 'LLM output could not be parsed: ' + str(plan_raw)[:1000]}

    with open(output_file, 'w') as f:
        f.write(markdown)

    verify = execute_shell_command('ls -la ' + output_file + ' && echo ---SIZE--- && wc -c ' + output_file)

    summary = call_llm(
        system='You are a report summarizer. Write a concise SUMMARY describing the markdown file written: its filename, structure, and key contents.',
        messages=[{'role': 'user', 'content': 'Request: ' + query + '\n\nFile written: ' + output_file + '\nMarkdown:\n' + markdown}],
        max_tokens=1200,
    )
    return {'answer': 'Wrote markdown to ' + output_file + ' (' + str(len(markdown)) + ' chars). Verify: ' + verify[:400], 'summary': summary}
