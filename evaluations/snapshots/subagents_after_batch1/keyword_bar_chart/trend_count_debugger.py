import json
from tools import execute_shell_command


def _run(cmd):
    try:
        return execute_shell_command(cmd)
    except Exception as e:
        return 'ERROR: ' + str(e)


def main(query: str) -> dict:
    out = _run("curl -s -L -A 'Mozilla/5.0' --max-time 30 'https://mastodon.social/api/v1/trends/tags?limit=40'")
    info = {}
    info['mastodon_len'] = len(out)
    try:
        data = json.loads(out)
        info['mastodon_count'] = len(data) if isinstance(data, list) else 'not-a-list'
        if isinstance(data, list) and data:
            sample = data[0]
            info['sample_keys'] = list(sample.keys()) if isinstance(sample, dict) else str(type(sample))
            info['sample'] = json.dumps(sample, ensure_ascii=False)[:800]
        info['names'] = [d.get('name') for d in data if isinstance(d, dict)][:40]
    except Exception as e:
        info['mastodon_parse_error'] = str(e)
        info['preview'] = out[:500]

    # also try statuses endpoint for additional keywords
    out2 = _run("curl -s -L -A 'Mozilla/5.0' --max-time 30 'https://mastodon.social/api/v1/trends/statuses?limit=20'")
    info['statuses_len'] = len(out2)
    try:
        d2 = json.loads(out2)
        info['statuses_count'] = len(d2) if isinstance(d2, list) else 'not-a-list'
    except Exception as e:
        info['statuses_parse_error'] = str(e)

    return {'answer': json.dumps(info, ensure_ascii=False), 'summary': 'debug: ' + json.dumps(info, ensure_ascii=False)[:1500]}
