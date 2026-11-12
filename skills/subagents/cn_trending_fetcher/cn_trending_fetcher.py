import json
from llm import call_llm
from tools import execute_shell_command


def main(query: str) -> dict:
    # General fetcher for REAL Chinese social-media trending/hot-search data.
    # Uses direct platform JSON endpoints (verified reachable): Weibo, Douyin, Baidu.
    # Parsing is deterministic per known schema, with an LLM fallback for unknown shapes.
    # Writes trending_keywords.json with top-N {keyword,count} rows.

    plan = call_llm(
        system='You parse requests for trending/hot-search data. Return JSON only.',
        messages=[{'role': 'user', 'content': 'Query: ' + query + '\n\nExtract the requested data shape. Return JSON: {"source_preference": "weibo|douyin|baidu|any", "top_n": <int default 20>}. Default top_n=20 if unspecified.'}],
        max_tokens=300,
    )
    try:
        s = plan.find('{'); e = plan.rfind('}')
        p = json.loads(plan[s:e + 1])
    except Exception:
        p = {}
    top_n = int(p.get('top_n', 20) or 20)
    pref = str(p.get('source_preference', 'any')).lower()

    # Verified-reachable direct Chinese platform endpoints with their parsers.
    def parse_weibo(d):
        items = []
        realtime = (d.get('data') or {}).get('realtime') or []
        for it in realtime:
            w = it.get('word') or it.get('note') or ''
            n = it.get('num') or it.get('raw_hot') or 0
            if w:
                items.append({'keyword': str(w).strip(), 'count': float(n or 0)})
        return items

    def parse_douyin(d):
        items = []
        data = d.get('data') or {}
        lst = data.get('word_list') or data.get('list') or (data if isinstance(data, list) else [])
        if isinstance(lst, list):
            for it in lst:
                if not isinstance(it, dict):
                    continue
                w = it.get('word') or it.get('sentence_tag') or ''
                n = it.get('hot_value') or it.get('hot_score') or 0
                if w:
                    items.append({'keyword': str(w).strip(), 'count': float(n or 0)})
        return items

    def parse_baidu(d):
        items = []
        try:
            cards = (d.get('data') or {}).get('cards') or []
            content = cards[0]['content'][0]['content']
            for it in content:
                w = it.get('word') or it.get('query') or ''
                n = it.get('hotScore') or it.get('hot') or 0
                if w:
                    items.append({'keyword': str(w).strip(), 'count': float(n or 0)})
        except Exception:
            pass
        return items

    sources = [
        {'name': 'weibo', 'url': 'https://weibo.com/ajax/side/hotSearch', 'parser': parse_weibo, 'referer': 'https://weibo.com/'},
        {'name': 'douyin', 'url': 'https://www.douyin.com/aweme/v1/web/hot/search/list/', 'parser': parse_douyin, 'referer': 'https://www.douyin.com/'},
        {'name': 'baidu', 'url': 'https://top.baidu.com/api/board?platform=wise&tab=realtime', 'parser': parse_baidu, 'referer': 'https://top.baidu.com/'},
    ]
    if pref in ('weibo', 'douyin', 'baidu'):
        sources.sort(key=lambda s: 0 if s['name'] == pref else 1)

    hdrs = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36', 'Accept': 'application/json, text/plain, */*'}

    tried_log = []
    chosen_name = None
    final_items = []

    for src in sources:
        hdrs['Referer'] = src.get('referer', '')
        # Write a small python fetch script per source to control headers reliably.
        py = (
            'import json, ssl, urllib.request\n'
            'url=' + repr(src['url']) + '\n'
            'h=' + repr(hdrs) + '\n'
            'ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE\n'
            'req=urllib.request.Request(url, headers=h)\n'
            'r=urllib.request.urlopen(req, timeout=25, context=ctx)\n'
            "open('raw_src.json','wb').write(r.read())\n"
        )
        with open('fetch_src.py', 'w', encoding='utf-8') as f:
            f.write(py)
        execute_shell_command('python3 fetch_src.py 2>&1 | head -c 500')
        try:
            with open('raw_src.json', 'r', encoding='utf-8', errors='replace') as f:
                raw = f.read()
        except Exception as e:
            tried_log.append(src['name'] + ': read_error ' + str(e))
            continue
        tried_log.append(src['name'] + ': ' + str(len(raw)) + ' chars')
        if len(raw.strip()) < 30:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            tried_log.append(src['name'] + ': NOT_JSON')
            continue
        items = src['parser'](data)
        tried_log.append(src['name'] + ': parsed ' + str(len(items)) + ' items')
        if items:
            # If parser failed on shape, fallback to LLM extraction
            pass
        if not items:
            ext = call_llm(
                system='Extract trending topics with numeric heat from JSON. Output JSON only.',
                messages=[{'role': 'user', 'content': 'From this JSON, extract a list of trending topics each with a title and numeric heat/popularity. Return JSON: {"items":[{"keyword":"...","count":<number>}]}. Do not invent numbers. JSON:\n' + raw[:6000]}],
                max_tokens=2000,
            )
            try:
                s = ext.find('{'); e = ext.rfind('}')
                items = json.loads(ext[s:e + 1]).get('items', [])
                items = [{'keyword': str(x['keyword']).strip(), 'count': float(x.get('count', 0))} for x in items if x.get('keyword')]
            except Exception:
                items = []
        if items:
            # dedupe & sort
            seen = {}
            for it in items:
                k = it['keyword']
                if not k:
                    continue
                seen[k] = max(seen.get(k, 0), it['count'])
            ranked = sorted([{'keyword': k, 'count': c} for k, c in seen.items()], key=lambda x: x['count'], reverse=True)
            final_items = ranked[:top_n]
            chosen_name = src['name']
            break

    result = {
        'query': query,
        'source': chosen_name or 'none',
        'top_n': top_n,
        'items': final_items,
        'fetch_log': tried_log,
    }
    with open('trending_keywords.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    summary = call_llm(
        system='You are a research summarizer. Write a clear SUMMARY of the data-fetching process and results.',
        messages=[{'role': 'user', 'content': 'Query: ' + query + '\n\nFetch log:\n' + '\n'.join(tried_log) + '\n\nChosen source: ' + str(chosen_name) + '\n\nTop items (up to 20):\n' + json.dumps(final_items, ensure_ascii=False)[:2500] + '\n\nWrite a SUMMARY (100-600 words): which Chinese platform was used, whether the data is real trending-frequency data, the top keywords and their heat counts, how many items were found, and caveats.'}],
        max_tokens=1500,
    )
    answer = 'Fetched ' + str(len(final_items)) + ' real trending topics from ' + str(chosen_name) + '; saved to trending_keywords.json'
    return {'answer': answer, 'summary': summary}
