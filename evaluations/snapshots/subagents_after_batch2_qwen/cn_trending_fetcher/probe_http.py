
import json, ssl, urllib.request
urls = json.loads(r'''[["vvhan-weibo", "https://api.vvhan.com/api/hotlist/wbHot"], ["vvhan-baidu", "https://api.vvhan.com/api/hotlist/baiduRD"], ["vvhan-zhihu", "https://api.vvhan.com/api/hotlist/zhihuHot"], ["freehot-weibo", "https://api-hot.imsyy.top/weibo"], ["freehot-baidu", "https://api-hot.imsyy.top/baidu"], ["freehot-zhihu", "https://api-hot.imsyy.top/zhihu"], ["60s-weibo", "https://60s.viki.moe/v2/weibo"], ["60s-baidu", "https://60s.viki.moe/v2/baidu/hot"], ["60s-zhihu", "https://60s.viki.moe/v2/zhihu"], ["dailyhot-deploy", "https://api-hot.efaz.dev/weibo"], ["rebang-weibo", "https://api.rebang.today/v1/items?tab=top&sub_tab=weibo"]]''')
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
