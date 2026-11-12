import json
from llm import call_llm
from tools import execute_shell_command


def _run_cmd(cmd):
    try:
        return execute_shell_command(cmd)
    except Exception as e:
        return f'ERROR: {e}'


def main(query: str) -> dict:
    plan_prompt = (
        'The user wants trending keyword/topic FREQUENCY data from a social media platform '
        '(or comparable public trending source), then the top N displayed as a bar chart.\n\n'
        f'User query: {query}\n\n'
        'Pick 2-3 concrete PUBLIC data sources that expose real trending topics WITH '
        'frequency/count data via a plain HTTP endpoint (no login/API key required if possible). '
        'Good candidates: Mastodon public trends https://mastodon.social/api/v1/trends/tags ; '
        'Wikimedia top pageviews https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access/2024/01/01 ; '
        'Bluesky public API; any public trending-tags JSON API.\n\n'
        'Return ONLY a JSON object of this exact shape:\n'
        '{"top_n": 20, "sources": [{"name": "short name", "url": "full https URL that returns JSON", "note": "why"}]}\n'
        'Pick real, currently-valid endpoints. Do not invent URLs you are unsure about.'
    )
    # Always prioritize SOCIAL MEDIA sources. We aggregate tags from multiple
    # social endpoints so we can reach the requested top N from social platforms.
    SOCIAL_SOURCES = [
        {'name': 'mastodon.social', 'url': 'https://mastodon.social/api/v1/trends/tags?limit=40'},
        {'name': 'mastodon.social', 'url': 'https://mastodon.social/api/v1/trends/statuses?limit=40'},
        {'name': 'mstdn.social', 'url': 'https://mstdn.social/api/v1/trends/tags?limit=40'},
        {'name': 'fosstodon', 'url': 'https://fosstodon.org/api/v1/trends/tags?limit=40'},
        {'name': 'mas.to', 'url': 'https://mas.to/api/v1/trends/tags?limit=40'},
        {'name': 'mastodon.online', 'url': 'https://mastodon.online/api/v1/trends/tags?limit=40'},
        {'name': 'hachyderm', 'url': 'https://hachyderm.io/api/v1/trends/tags?limit=40'},
        {'name': 'infosec.exchange', 'url': 'https://infosec.exchange/api/v1/trends/tags?limit=40'},
    ]
    top_n = 20
    sources = SOCIAL_SOURCES

    collected = []
    tried_log = []

    def extract(out, src_name):
        extract_prompt = (
            f'Here is RAW JSON fetched from a trending-topics endpoint ({src_name}).\n'
            'Extract the trending keywords/topics and, for each, a NUMERIC frequency/count measure. '
            'If the JSON has no explicit count field, derive a count from available numeric fields '
            "(e.g. 'uses', 'uses_count', number of related accounts, 'views', likes, etc.). Do NOT invent numbers.\n\n"
            'Return ONLY a JSON object: '
            '{"items": [{"keyword": "...", "count": <number>}, ...]}\n'
            f'Sort by count descending, keep at most {top_n} items.\n\n'
            f'RAW JSON (may be truncated):\n{out[:6000]}\n'
        )
        ext_raw = call_llm(
            system='You extract structured numeric data from JSON. Output only valid JSON.',
            messages=[{'role': 'user', 'content': extract_prompt}],
            max_tokens=2000,
        )
        try:
            s = ext_raw.find('{'); e = ext_raw.rfind('}')
            items = json.loads(ext_raw[s:e + 1]).get('items', [])
        except Exception:
            items = []
        clean = []
        for it in items:
            try:
                kw = str(it.get('keyword', '')).strip()
                ct = float(it.get('count', 0))
                if kw and ct >= 0:
                    clean.append({'source': src_name, 'keyword': kw, 'count': ct})
            except Exception:
                continue
        return clean

    # IMPORTANT: execute_shell_command truncates stdout at 5000 chars, corrupting
    # large JSON. So fetch to a FILE with curl, then read the file back fully.
    def fetch_to_file(url, path):
        _run_cmd("curl -s -L -A 'Mozilla/5.0' --max-time 30 -o '" + path + "' '" + url + "'")
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        except Exception as e:
            return 'ERROR: ' + str(e)

    for src in sources:
        url = src.get('url')
        if not url:
            continue
        sep = '&' if '?' in url else '?'
        fetch_url = url if ('limit=' in url) else (url + sep + 'limit=40')
        out = fetch_to_file(fetch_url, 'raw_source.json')
        tried_log.append('URL ' + fetch_url + ' -> ' + str(len(out)) + ' chars')
        if not out or out.startswith('ERROR') or len(out.strip()) < 20:
            continue
        clean_items = extract(out, src.get('name', 'source'))
        if clean_items:
            collected.extend(clean_items)
            tried_log.append('Extracted ' + str(len(clean_items)) + ' items from ' + str(src.get('name')))
            if len(clean_items) >= top_n:
                break

    if len(collected) < top_n:
        st_out = fetch_to_file('https://mastodon.social/api/v1/trends/statuses?limit=40', 'raw_statuses.json')
        tried_log.append('statuses endpoint -> ' + str(len(st_out)) + ' chars')
        if st_out and not st_out.startswith('ERROR'):
            st_items = extract(st_out, 'Mastodon trends/statuses')
            if st_items:
                collected.extend(st_items)
                tried_log.append('Extracted ' + str(len(st_items)) + ' items from statuses')

    if not collected:
        out = fetch_to_file('https://mastodon.social/api/v1/trends/tags?limit=40', 'raw_fallback.json')
        tried_log.append('Direct mastodon fallback -> ' + str(len(out)) + ' chars')
        collected = extract(out, 'mastodon')

    # Deterministic direct-parse augmentation: if we still lack top_n unique items,
    # parse the known Mastodon JSON schema ourselves (tags carry name + history.uses;
    # statuses carry a 'tags' array of {name}). This is more reliable than LLM extraction.
    if len({c['keyword'].lower() for c in collected}) < top_n:
        def parse_mastodon_json(text, src_name):
            got = []
            try:
                data = json.loads(text)
            except Exception:
                return got
            if not isinstance(data, list):
                return got
            for obj in data:
                if not isinstance(obj, dict):
                    continue
                # tags endpoint shape
                if 'name' in obj and 'history' in obj and isinstance(obj['history'], list):
                    uses = 0.0
                    for h in obj['history']:
                        try:
                            uses += float(h.get('uses', 0))
                        except Exception:
                            pass
                    if obj['name']:
                        got.append({'source': src_name, 'keyword': str(obj['name']), 'count': uses})
                # statuses endpoint shape: 'tags': [{'name':...}]
                elif isinstance(obj.get('tags'), list):
                    base = 0.0
                    try:
                        base = float(obj.get('reblogs_count', 0)) + float(obj.get('favourites_count', 0))
                    except Exception:
                        base = 0.0
                    for t in obj['tags']:
                        if isinstance(t, dict) and t.get('name'):
                            got.append({'source': src_name, 'keyword': str(t['name']), 'count': max(base, 1.0)})
            return got

        for path, src_name in [('raw_source.json', 'mastodon.social'), ('raw_statuses.json', 'mastodon.social'), ('raw_fallback.json', 'mastodon')]:
            try:
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    txt = f.read()
            except Exception:
                continue
            got = parse_mastodon_json(txt, src_name)
            if got:
                collected.extend(got)
                tried_log.append('Direct-parse ' + path + ': ' + str(len(got)) + ' tags')

    # Normalize + dedupe by lowercased keyword, summing counts for same tag across sources,
    # and merge simple singular/plural like 'redpanda'/'redpandas'.
    agg = {}
    for row in collected:
        kw = row['keyword'].strip().lstrip('#').lower()
        if not kw:
            continue
        agg[kw] = agg.get(kw, 0.0) + float(row['count'])
    merged = {}
    for kw, ct in agg.items():
        base = kw[:-1] if kw.endswith('s') and len(kw) > 3 and kw[:-1] in agg else kw
        merged[base] = merged.get(base, 0.0) + ct
    final_items = sorted(
        [{'source': 'Mastodon', 'keyword': kw, 'count': ct} for kw, ct in merged.items()],
        key=lambda x: x['count'], reverse=True,
    )[:top_n]

    result_data = {
        'query': query,
        'source': final_items[0]['source'] if final_items else 'unknown',
        'top_n': top_n,
        'items': final_items,
        'fetch_log': tried_log,
    }
    with open('trending_keywords.json', 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    summary = call_llm(
        system='You are a research summarizer. Write a clear SUMMARY of the data-fetching process and results.',
        messages=[{'role': 'user', 'content': 'Query: ' + query + '\n\nFetch log:\n' + '\n'.join(tried_log[-8:]) + '\n\nTop extracted items (up to 20):\n' + json.dumps(final_items, ensure_ascii=False)[:2500] + '\n\nWrite a SUMMARY (100-500 words) describing which source(s) were used, whether the data is real frequency data, what the top keywords and counts are, and any caveats. State the number of items found.'}],
        max_tokens=1500,
    )
    answer = f"Fetched {len(final_items)} trending keywords with frequency counts from {result_data['source']}; saved to trending_keywords.json"
    return {'answer': answer, 'summary': summary}
