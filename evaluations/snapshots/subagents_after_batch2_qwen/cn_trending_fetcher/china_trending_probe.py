import json
from llm import call_llm
from tools import execute_shell_command


def main(query: str) -> dict:
    candidates = [
        ('vvhan-weibo', 'https://api.vvhan.com/api/hotlist/wbHot'),
        ('vvhan-baidu', 'https://api.vvhan.com/api/hotlist/baiduRD'),
        ('vvhan-zhihu', 'https://api.vvhan.com/api/hotlist/zhihuHot'),
        ('vvhan-douyin', 'https://api.vvhan.com/api/hotlist/douyinHot'),
        ('vvhan-bilibili', 'https://api.vvhan.com/api/hotlist/bili'),
        ('tenapi-weibo', 'https://tenapi.cn/v2/weibohot'),
        ('tenapi-baidu', 'https://tenapi.cn/v2/baiduhot'),
        ('tenapi-douyin', 'https://tenapi.cn/v2/douyinhot'),
        ('tenapi-zhihu', 'https://tenapi.cn/v2/zhihuhot'),
        ('freehot-weibo', 'https://api-hot.imsyy.top/weibo'),
        ('freehot-baidu', 'https://api-hot.imsyy.top/baidu'),
        ('freehot-zhihu', 'https://api-hot.imsyy.top/zhihu'),
        ('freehot-douyin', 'https://api-hot.imsyy.top/douyin'),
        ('freehot-bilibili', 'https://api-hot.imsyy.top/bilibili'),
    ]

    results = []
    for name, url in candidates:
        path = 'probe_' + name + '.json'
        cmd = "curl -s -L -A 'Mozilla/5.0' --max-time 20 -o '" + path + "' '" + url + "'"
        try:
            execute_shell_command(cmd)
        except Exception as e:
            results.append({'name': name, 'url': url, 'status': 'curl_error', 'err': str(e)})
            continue
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                raw = f.read()
        except Exception as e:
            results.append({'name': name, 'url': url, 'status': 'read_error', 'err': str(e)})
            continue
        stripped = raw.strip()
        ok_json = False
        preview = stripped[:300]
        try:
            data = json.loads(stripped)
            ok_json = True
            if isinstance(data, dict):
                shape = list(data.keys())
            elif isinstance(data, list):
                shape = ['list len=' + str(len(data))]
            else:
                shape = ['other']
        except Exception:
            shape = ['NOT_JSON']
        results.append({
            'name': name,
            'url': url,
            'len': len(stripped),
            'json': ok_json,
            'shape': shape,
            'preview': preview,
        })

    analysis = call_llm(
        system='You are a debugging analyst. Given probe results from candidate trending JSON endpoints, identify which returned valid JSON with a list of trending topics that include a title/name and a numeric heat/count field. Output concise findings.',
        messages=[{'role': 'user', 'content': 'Probe results:\n' + json.dumps(results, ensure_ascii=False, indent=2)[:6000] + '\n\nReport per-endpoint: usable? (yes/no), and if usable, the field paths for title and heat/count (e.g. data[].title, data[].hot). Recommend the best 2 sources.'}],
        max_tokens=1500,
    )

    summary = call_llm(
        system='You are a research summarizer. Write a detailed SUMMARY of the endpoint-probing process and findings.',
        messages=[{'role': 'user', 'content': 'Query: ' + query + '\n\nRaw probe results:\n' + json.dumps(results, ensure_ascii=False, indent=2)[:5000] + '\n\nAnalysis:\n' + analysis + '\n\nWrite a SUMMARY (100-800 words) describing which endpoints were reachable, which returned usable structured trending data, their schemas, and a recommendation.'}],
        max_tokens=2000,
    )

    usable = [r for r in results if r.get('json') and r.get('len', 0) > 50]
    answer = 'Probed ' + str(len(candidates)) + ' endpoints; ' + str(len(usable)) + ' returned parseable JSON.'
    return {'answer': answer, 'summary': summary + '\n\nANALYSIS:\n' + analysis}
