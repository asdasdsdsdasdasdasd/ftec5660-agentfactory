import os
from llm import call_llm
from tools import execute_shell_command


def main(query: str) -> dict:
    # LLM parses the query to find what file to inspect and what to verify
    plan_raw = call_llm(
        system="You parse file-inspection requests. Return ONLY a JSON object with keys: 'filename' (the target file path or name), 'verify' (short description of what to check). Return ONLY valid JSON.",
        messages=[{'role':'user','content':'Request: ' + query}],
        max_tokens=300,
    )
    import json, re
    t = re.sub(r'^```(?:json)?','',plan_raw.strip()).strip()
    t = re.sub(r'```$','',t).strip()
    m = re.search(r'\{.*\}', t, re.DOTALL)
    plan = json.loads(m.group(0)) if m else {}
    filename = plan.get('filename','')
    verify = plan.get('verify','verify file exists and has content')

    log = []
    log.append('Inspecting: ' + str(filename))
    ls = execute_shell_command('ls -la ' + str(filename))
    log.append('ls output: ' + str(ls))
    exists = ('No such file' not in str(ls)) and ('cannot access' not in str(ls).lower())

    content = ''
    if exists:
        content = execute_shell_command('cat ' + str(filename))
        wc = execute_shell_command('wc -l ' + str(filename))
        log.append('wc: ' + str(wc))
    else:
        # try to locate the file
        found = execute_shell_command('find . -name "' + os.path.basename(str(filename)) + '" 2>/dev/null')
        log.append('find result: ' + str(found))

    answer = call_llm(
        system='You are a file verification assistant. Given the file status, log, and content, answer whether the file exists and what it contains. Be factual.',
        messages=[{'role':'user','content':'File: ' + str(filename) + '\nVerify: ' + verify + '\nExists: ' + str(exists) + '\nContent:\n' + str(content)[:4000]}],
        max_tokens=800,
    )

    summary = call_llm(
        system='Write a concise SUMMARY of the file inspection: what was checked, whether it exists, and key content evidence.',
        messages=[{'role':'user','content':'Request: ' + query + '\nLog:\n' + '\n'.join(log) + '\nAnswer: ' + answer}],
        max_tokens=600,
    )
    return {'answer': answer, 'summary': summary}
