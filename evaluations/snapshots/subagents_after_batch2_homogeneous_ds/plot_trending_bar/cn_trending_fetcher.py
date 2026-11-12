import json, os, re
from llm import call_llm
from tools import execute_shell_command


def fetch_url_to_file(url, path, referer=None):
    hdr = "-H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36' -H 'Accept: application/json, text/plain, */*' -H 'Accept-Language: zh-CN,zh;q=0.9,en;q=0.8'"
    if referer:
        hdr += f" -H 'Referer: {referer}'"
    cmd = f"curl -sL --max-time 25 --compressed {hdr} '{url}' -o '{path}' ; echo EXIT=$?; wc -c '{path}' 2>/dev/null"
    return execute_shell_command(cmd)


def parse_weibo(data):
    out = []
    realtime = None
    if isinstance(data, dict):
        if isinstance(data.get('data'), dict):
            realtime = data['data'].get('realtime')
        if realtime is None:
            realtime = data.get('band_list') or data.get('realtime') or data.get('data')
    for item in (realtime or []):
        if not isinstance(item, dict):
            continue
        title = item.get('word') or item.get('note') or item.get('name')
        heat = item.get('num') or item.get('raw_hot') or item.get('hot_value') or item.get('hot_nums') or 0
        try: heat = int(heat)
        except: heat = 0
        if title:
            out.append({'title': str(title), 'heat': heat})
    return out


def parse_zhihu(data):
    out = []
    items = data.get('data', []) if isinstance(data, dict) else []
    for it in items:
        if not isinstance(it, dict):
            continue
        target = it.get('target', {}) or {}
        title = target.get('title')
        detail = it.get('detail_text') or ''
        heat = 0
        m = re.search(r'([0-9.]+)\s*万', detail)
        if m:
            heat = int(float(m.group(1)) * 10000)
        else:
            m2 = re.search(r'([0-9]+)', detail)
            if m2: heat = int(m2.group(1))
        if title:
            out.append({'title': str(title), 'heat': heat})
    return out


def parse_toutiao(data):
    out = []
    items = data.get('data', []) if isinstance(data, dict) else []
    for it in items:
        if not isinstance(it, dict): continue
        title = it.get('Title') or it.get('title')
        heat = it.get('HotValue') or it.get('hot_value') or 0
        try: heat = int(heat)
        except: heat = 0
        if title: out.append({'title': str(title), 'heat': heat})
    return out


def parse_douyin(data):
    out = []
    d = data.get('data') or {} if isinstance(data, dict) else {}
    words = d.get('word_list') or d.get('list') or []
    for w in words:
        if isinstance(w, dict):
            title = w.get('word') or w.get('sentence') or w.get('title')
            heat = w.get('hot_value') or w.get('hot_score') or 0
            try: heat = int(heat)
            except: heat = 0
            if title: out.append({'title': str(title), 'heat': heat})
    return out


def parse_baidu_html(html):
    out = []
    titles = re.findall(r'"word"\s*:\s*"([^"]+)"', html)
    heats = re.findall(r'"hotScore"\s*:\s*"?([0-9]+)"?', html)
    if not titles:
        titles = re.findall(r'"query"\s*:\s*"([^"]+)"', html)
    for i, t in enumerate(titles):
        h = int(heats[i]) if i < len(heats) else 0
        out.append({'title': t, 'heat': h})
    return out


PARSERS = {
    'weibo_json': parse_weibo, 'zhihu_json': parse_zhihu, 'toutiao_json': parse_toutiao,
    'douyin_json': parse_douyin, 'baidu_html': parse_baidu_html,
}

SOURCES = [
    ('weibo_hot', 'https://weibo.com/ajax/side/hotSearch', 'weibo_json', None),
    ('zhihu_hot', 'https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=50', 'zhihu_json', None),
    ('toutiao_hot', 'https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc', 'toutiao_json', None),
    ('douyin_hot', 'https://www.iesdouyin.com/web/api/v2/hotsearch/billboard/word/', 'douyin_json', None),
    ('baidu_hot', 'https://top.baidu.com/board?tab=realtime', 'baidu_html', None),
]


def main(query):
    evidence = [f'Query: {query}']
    all_items = []
    used_source = None

    for name, url, parser_name, referer in SOURCES:
        path = f'/tmp/trend_{name}.dat'
        info = fetch_url_to_file(url, path, referer)
        size = 0
        try: size = os.path.getsize(path)
        except: pass
        evidence.append(f'[{name}] {info.strip()[-80:]} size={size}')
        if size < 50:
            continue
        raw = open(path, 'r', encoding='utf-8', errors='ignore').read()
        items = []
        if parser_name.endswith('_json'):
            try:
                items = PARSERS[parser_name](json.loads(raw))
            except Exception as e:
                evidence.append(f'[{name}] json err: {e}')
        else:
            items = PARSERS[parser_name](raw)
        if not items:
            try:
                raw2 = call_llm(system='Extract a trending topic list from the raw text. Return ONLY a JSON array of {"title":str,"heat":int}. Return [] if none. Preserve original language.', messages=[{'role':'user','content':raw[:8000]}])
                m = re.search(r'\[.*\]', raw2, re.S)
                if m: items = json.loads(m.group(0))
            except Exception as e:
                evidence.append(f'[{name}] llm extract err: {e}')
        evidence.append(f'[{name}] parsed {len(items)} items')
        if len(items) >= 5:
            all_items = items
            used_source = name
            break

    if not all_items:
        summary = call_llm(system='Write a brief failure summary from the evidence.', messages=[{'role':'user','content':'Failed to fetch Chinese trending topics. Evidence:\n' + '\n'.join(evidence)}])
        return {'answer': 'FAILED to fetch trending topics from any source.', 'summary': summary}

    seen = set(); clean = []
    for it in all_items:
        t = str(it.get('title','')).strip()
        if not t or t in seen: continue
        seen.add(t)
        try: h = int(it.get('heat',0))
        except: h = 0
        clean.append({'title': t, 'heat': h})

    top20 = clean[:20]
    with open('trending_topics.json','w',encoding='utf-8') as f:
        json.dump({'source': used_source, 'top_n': len(top20), 'items': top20, 'fetch_log': evidence}, f, ensure_ascii=False, indent=2)

    summary = call_llm(system='You are a research summarizer. Write a detailed SUMMARY of the trending topic fetch process.', messages=[{'role':'user','content': f'Query: {query}\nSource used: {used_source}\nTop items: {json.dumps(top20, ensure_ascii=False)}\nFetch log:\n' + '\n'.join(evidence) + '\n\nWrite a SUMMARY (100-500 words) tracing sources tried, what worked, and the resulting top-20.'}])
    return {'answer': f'Fetched {len(top20)} trending topics from {used_source}. Saved to trending_topics.json.', 'summary': summary}
