import json
from llm import call_llm
from tools import execute_shell_command

SYSPROMPT = ('You are a shell task planner. Convert the user request into a JSON array of concrete, '
             'NON-INTERACTIVE bash commands to run in order. Each command must be safe '
             '(no rm/rmdir/shred, no interactive editors, no long-running foreground programs). '
             'Use head/tail/sed/grep/cat -n/wc for inspecting files. '
             'Return ONLY a JSON array of strings and no prose.')


def main(query: str) -> dict:
    evidence = []
    plan = call_llm(
        system=SYSPROMPT,
        messages=[{'role': 'user', 'content': 'Request: ' + query}],
        max_tokens=1200,
    )
    cmds = []
    try:
        start = plan.find('[')
        end = plan.rfind(']')
        if start != -1 and end != -1:
            cmds = json.loads(plan[start:end + 1])
    except Exception as e:
        evidence.append('PLAN_PARSE_ERROR: ' + str(e) + chr(10) + 'RAW_PLAN:' + chr(10) + plan)
    if not cmds:
        cmds = [query]
    raw_outputs = []
    for c in cmds[:12]:
        if not isinstance(c, str):
            continue
        out = execute_shell_command(c + ' 2>&1')
        raw_outputs.append('$ ' + c + chr(10) + out)
        evidence.append('CMD: ' + c + chr(10) + out)
    combined = (chr(10) + chr(10)).join(raw_outputs)
    summary = call_llm(
        system='You are a technical reporter. Summarize what the shell commands returned, quoting raw outputs verbatim where relevant.',
        messages=[{'role': 'user', 'content': 'Request: ' + query + chr(10) + 'Commands and outputs:' + chr(10) + combined[:6000] + chr(10) + 'Write a factual SUMMARY of findings.'}],
        max_tokens=2000,
    )
    return {'answer': combined[:4500], 'summary': summary}
