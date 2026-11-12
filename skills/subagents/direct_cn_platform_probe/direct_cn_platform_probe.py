import json
from llm import call_llm
from tools import execute_shell_command


def main(query: str) -> dict:
    # Probe DIRECT Chinese social-media platform endpoints (the authentic sources),
    # plus a couple of working aggregators, and report which return valid JSON.
    candidates = [
        ('weibo-hotsearch', 'https://weibo.com/ajax/side/hotSearch'),
        ('weibo-mobile', 'https://m.weibo.cn/api/container/getIndex?containerid=106003type%3D25%26t%3D3%26disable_hot%3D1%26filter_type%3Drealtimehot'),
        ('baidu-top', 'https://top.baidu.com/api/board?platform=wise&tab=realtime'),
        ('zhihu-hot', 'https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=50'),
        ('bilibili-rank', 'https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all'),
        ('douyin-hot', 'https://www.douyin.com/aweme/v1/web/hot/search/list/'),
        ('60s-weibo', 'https://60s.viki.moe/v2/weibo'),
        ('60s-baidu', 'https://60s.viki.moe/v2/baidu/hot'),
    ]
    urls = [[n, u] for n, u in candidates]
    py = r'''
import json, ssl, urllib.request
urls = json.loads(r''' + "'''" + json.dumps(urls) + "'''" + r''')
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
hdrs = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36', 'Accept': 'application/json, text/plain, */*', 'Referer': 'https://weibo.com/'}
out = []
for name, url in urls:
    rec = {'name': name, 'url': url}
    try:
        req = urllib.request.Request(url, headers=hdrs)
        with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
            body = r.read()
            rec['status'] = r.status
            rec['len'] = len(body)
            txt = body.decode('utf-8', 'replace')
            rec['preview'] = txt[:350]
            try:
                d = json.loads(txt)
                rec['json'] = True
                if isinstance(d, dict):
                    rec['keys'] = list(d.keys())[:15]
                elif isinstance(d, list):
                    rec['list_len'] = len(d)
                    if d and isinstance(d[0], dict):
                        rec['item_keys'] = list(d[0].keys())[:20]
            except Exception:
                rec['json'] = False
    except Exception as e:
        rec['error'] = str(e)[:250]
    out.append(rec)
print(json.dumps(out, ensure_ascii=False))
'''
    with open('probe_direct.py', 'w', encoding='utf-8') as f:
        f.write(py)
    raw = execute_shell_command('python3 probe_direct.py 2>&1 | head -c 5000')
    try:
        results = json.loads(raw[raw.find('['):raw.rfind(']') + 1])
    except Exception:
        results = [{'raw_output': raw[:4500]}]

    analysis = call_llm(
        system='You are a debugging analyst. Given diagnostics from Chinese social-media trending endpoints, identify which return valid JSON containing a list of hot topics with a title string and a numeric heat/popularity value. Give exact JSON paths to the list and the title/heat field names.',
        messages=[{'role': 'user', 'content': 'Diagnostics:\n' + json.dumps(results, ensure_ascii=False, indent=2)[:6000] + '\n\nFor each endpoint: usable yes/no + reason; if usable give exact list path and field names for title and heat. Rank the best options.'}],
        max_tokens=1800,
    )
    summary = call_llm(
        system='You are a research summarizer. Write a detailed SUMMARY.',
        messages=[{'role': 'user', 'content': 'Query: ' + query + '\n\nDiagnostics:\n' + json.dumps(results, ensure_ascii=False, indent=2)[:5000] + '\n\nAnalysis:\n' + analysis + '\n\nWrite a SUMMARY (150-800 words): which Chinese platform endpoints responded, HTTP status, whether valid trending JSON returned, exact schema for title & heat, and best sources.'}],
        max_tokens=2000,
    )
    usable = [r for r in results if isinstance(r, dict) and r.get('json')]
    answer = 'Probed ' + str(len(results)) + ' Chinese platform endpoints; ' + str(len(usable)) + ' returned valid JSON.'
    return {'answer': answer, 'summary': summary + '\n\nANALYSIS:\n' + analysis}
