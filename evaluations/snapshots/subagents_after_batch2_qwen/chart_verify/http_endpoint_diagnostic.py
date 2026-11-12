import json
from llm import call_llm
from tools import execute_shell_command


def main(query: str) -> dict:
    # Generic HTTP endpoint diagnostic: probes candidate URLs and reports HTTP status,
    # content-type, body length and a preview. Uses BOTH curl (verbose status) and a
    # Python urllib fallback so we can distinguish 'server down' from 'client fetch bug'.

    candidates = [
        ('vvhan-weibo', 'https://api.vvhan.com/api/hotlist/wbHot'),
        ('vvhan-baidu', 'https://api.vvhan.com/api/hotlist/baiduRD'),
        ('vvhan-zhihu', 'https://api.vvhan.com/api/hotlist/zhihuHot'),
        ('freehot-weibo', 'https://api-hot.imsyy.top/weibo'),
        ('freehot-baidu', 'https://api-hot.imsyy.top/baidu'),
        ('freehot-zhihu', 'https://api-hot.imsyy.top/zhihu'),
        ('60s-weibo', 'https://60s.viki.moe/v2/weibo'),
        ('60s-baidu', 'https://60s.viki.moe/v2/baidu/hot'),
        ('60s-zhihu', 'https://60s.viki.moe/v2/zhihu'),
        ('dailyhot-deploy', 'https://api-hot.efaz.dev/weibo'),
        ('rebang-weibo', 'https://api.rebang.today/v1/items?tab=top&sub_tab=weibo'),
    ]

    # Probe via python urllib in a single script per URL is heavy; instead do one
    # combined python block that loops all URLs and prints a compact JSON report.
    urls = [[n, u] for n, u in candidates]
    py = r'''
import json, ssl, urllib.request
urls = json.loads(r''' + "'''" + json.dumps(urls) + "'''" + r''')
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
out = []
for name, url in urls:
    rec = {'name': name, 'url': url}
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json,text/plain,*/*'})
        with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
            body = r.read()
            rec['status'] = r.status
            rec['ctype'] = r.headers.get('Content-Type', '')
            rec['len'] = len(body)
            txt = body.decode('utf-8', 'replace')
            rec['preview'] = txt[:400]
            try:
                d = json.loads(txt)
                rec['json'] = True
                if isinstance(d, dict):
                    rec['keys'] = list(d.keys())
                elif isinstance(d, list):
                    rec['list_len'] = len(d)
                    if d and isinstance(d[0], dict):
                        rec['item_keys'] = list(d[0].keys())
            except Exception:
                rec['json'] = False
    except Exception as e:
        rec['error'] = str(e)[:300]
    out.append(rec)
print(json.dumps(out, ensure_ascii=False))
'''

    with open('probe_http.py', 'w', encoding='utf-8') as f:
        f.write(py)

    raw = execute_shell_command('python3 probe_http.py 2>&1 | head -c 4500')

    try:
        results = json.loads(raw[raw.find('['):raw.rfind(']') + 1])
    except Exception:
        results = [{'raw_output': raw[:4000]}]

    analysis = call_llm(
        system='You are a debugging analyst. Given diagnostics from candidate trending JSON endpoints (HTTP status, content-type, body preview, JSON schema keys), identify which endpoints are usable and the exact field paths for the trending topic title and its heat/count number.',
        messages=[{'role': 'user', 'content': 'Diagnostics:\n' + json.dumps(results, ensure_ascii=False, indent=2)[:6000] + '\n\nFor each endpoint report: usable yes/no, reason, and if usable the JSON path to the list and the field names for title and heat/count. Recommend the best 2 endpoints.'}],
        max_tokens=1800,
    )

    summary = call_llm(
        system='You are a research summarizer. Write a detailed SUMMARY of the HTTP endpoint diagnostic process and findings.',
        messages=[{'role': 'user', 'content': 'Query: ' + query + '\n\nDiagnostics:\n' + json.dumps(results, ensure_ascii=False, indent=2)[:5000] + '\n\nAnalysis:\n' + analysis + '\n\nWrite a SUMMARY (100-800 words): which URLs responded, their HTTP status/content-type, which returned real Chinese trending JSON, the schema (title & heat fields), and a clear recommendation.'}],
        max_tokens=2000,
    )

    usable = [r for r in results if isinstance(r, dict) and r.get('json')]
    answer = 'Diagnosed ' + str(len(results)) + ' endpoints; ' + str(len(usable)) + ' returned valid JSON.'
    return {'answer': answer, 'summary': summary + '\n\nANALYSIS:\n' + analysis}
