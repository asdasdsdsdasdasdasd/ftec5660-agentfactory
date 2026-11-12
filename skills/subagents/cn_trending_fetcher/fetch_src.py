import json, ssl, urllib.request
url='https://weibo.com/ajax/side/hotSearch'
h={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36', 'Accept': 'application/json, text/plain, */*', 'Referer': 'https://weibo.com/'}
ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
req=urllib.request.Request(url, headers=h)
r=urllib.request.urlopen(req, timeout=25, context=ctx)
open('raw_src.json','wb').write(r.read())
