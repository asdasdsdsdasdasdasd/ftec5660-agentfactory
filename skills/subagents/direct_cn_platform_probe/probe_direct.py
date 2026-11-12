
import json, ssl, urllib.request
urls = json.loads(r'''[["weibo-hotsearch", "https://weibo.com/ajax/side/hotSearch"], ["weibo-mobile", "https://m.weibo.cn/api/container/getIndex?containerid=106003type%3D25%26t%3D3%26disable_hot%3D1%26filter_type%3Drealtimehot"], ["baidu-top", "https://top.baidu.com/api/board?platform=wise&tab=realtime"], ["zhihu-hot", "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=50"], ["bilibili-rank", "https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all"], ["douyin-hot", "https://www.douyin.com/aweme/v1/web/hot/search/list/"], ["60s-weibo", "https://60s.viki.moe/v2/weibo"], ["60s-baidu", "https://60s.viki.moe/v2/baidu/hot"]]''')
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
