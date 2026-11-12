import json
import re
from llm import call_llm
from tools import search_serper, read_url_jina


def _clean_json(text):
    if not text:
        return None
    t = text.strip()
    t = re.sub(r'^```(?:json)?', '', t).strip()
    t = re.sub(r'```$', '', t).strip()
    m = re.search(r'\{.*\}', t, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    try:
        return json.loads(t)
    except Exception:
        return None


def _fetch_text(url):
    try:
        content = read_url_jina(url)
    except Exception as e:
        return '', str(e)
    if isinstance(content, dict):
        if 'error' in content:
            return '', str(content.get('error'))
        return content.get('text', '') or '', None
    return (content or ''), None


def main(query: str) -> dict:
    log = []

    plan_raw = call_llm(
        system=(
            'You are a research task planner. Given a user research task that requires finding a web page '
            'and extracting a STRUCTURED LIST of items (e.g. lectures, chapters, products, entries) each with '
            'a title/topic and often a link, output ONLY a JSON object with keys: '
            'search_queries (list of 2-4 specific web search queries), '
            'preferred_site (domain substring if a specific site is requested else empty string), '
            'target_page (short description of exact page to open), '
            'list_description (what ordered list to extract), '
            'limit (integer max number of items requested or 0 if unspecified), '
            'fields (list of fields per item e.g. [topic, link]), '
            'output_file (markdown filename ending .md). Return ONLY valid JSON.'
        ),
        messages=[{'role': 'user', 'content': 'Research task: ' + query}],
        max_tokens=900,
    )
    plan = _clean_json(plan_raw) or {}
    search_queries = plan.get('search_queries') or [query]
    preferred = (plan.get('preferred_site') or '').strip().lower()
    target_page = plan.get('target_page', query)
    list_description = plan.get('list_description', 'items')
    try:
        limit = int(plan.get('limit') or 0)
    except Exception:
        limit = 0
    fields = plan.get('fields') or ['topic', 'link']
    output_file = plan.get('output_file') or 'extracted_list.md'
    if not output_file.endswith('.md'):
        output_file += '.md'
    log.append('Planned queries: ' + str(search_queries) + ' | preferred: ' + preferred + ' | limit: ' + str(limit))

    seen = set()
    candidates = []
    search_jobs = list(search_queries)
    if preferred:
        for q in list(search_queries):
            search_jobs.append(q + ' site:' + preferred)
    for q in search_jobs:
        try:
            results = search_serper(q, topk=8)
        except Exception as e:
            log.append('Search ' + q + ' failed: ' + str(e))
            continue
        if results and isinstance(results, list) and 'error' in results[0]:
            log.append('Search ' + q + ' error: ' + str(results[0]['error']))
            continue
        for r in results:
            link = r.get('link')
            if link and link not in seen:
                seen.add(link)
                candidates.append(r)
        log.append('Search ' + q + ' -> ' + str(len(results or [])) + ' results')

    def pref_rank(c):
        link = (c.get('link') or '').lower()
        return 0 if (preferred and preferred in link) else 1
    candidates.sort(key=pref_rank)
    shortlist = candidates[:12]
    listing = '\n'.join('[' + str(i) + '] ' + str(c.get('title','')) + ' | ' + str(c.get('link','')) + ' | ' + str(c.get('snippet',''))[:160] for i, c in enumerate(shortlist))

    rank_raw = call_llm(
        system='You choose the single BEST web page to open for extracting a structured list. Return ONLY JSON with index (int) and reason (short).',
        messages=[{'role': 'user', 'content': 'Target page: ' + target_page + '\nTask: ' + query + '\nPrefer domain: ' + preferred + '\n\nCandidates:\n' + listing}],
        max_tokens=300,
    )
    rank = _clean_json(rank_raw) or {}
    best_idx = rank.get('index', 0)
    if not isinstance(best_idx, int) or best_idx < 0 or best_idx >= len(shortlist):
        best_idx = 0
        if preferred:
            for i, c in enumerate(shortlist):
                if preferred in (c.get('link', '').lower()):
                    best_idx = i
                    break

    page_text = ''
    page_url = ''
    page_title = ''
    order = [best_idx] + [i for i in range(len(shortlist)) if i != best_idx]
    for idx in order:
        c = shortlist[idx]
        url = c.get('link')
        if not url:
            continue
        txt, err = _fetch_text(url)
        if not err and txt and len(txt) > 200:
            page_text = txt
            page_url = url
            page_title = c.get('title', '')
            log.append('Fetched ' + url + ' (' + str(len(txt)) + ' chars)')
            break
        else:
            log.append('Fetch failed/short for ' + str(url) + ': ' + str(err or 'too short'))

    if not page_text:
        summary = call_llm(
            system='Write a SUMMARY of the research attempt and why it failed.',
            messages=[{'role': 'user', 'content': 'Task: ' + query + '\nLog:\n' + '\n'.join(log)}],
            max_tokens=800,
        )
        return {'answer': 'Failed to fetch a suitable page.', 'summary': summary}

    limit_note = ('Return at most the first ' + str(limit) + ' items.') if limit > 0 else 'Return all items found.'
    extract_raw = call_llm(
        system=(
            'You are an expert reader that extracts ORDERED structured lists from web page content. '
            'Produce ONLY a JSON object with keys: '
            'page_title (page title), list_title (what the list is), '
            'items (an ordered JSON array; each element is an object with the requested fields; '
            'for a link field give an absolute URL resolved against the page URL if it is relative; '
            'if a link is not present use empty string). '
            'Only use information actually present in the page. Return ONLY valid JSON.'
        ),
        messages=[{'role': 'user', 'content': 'Task: ' + query + '\nExtract this ordered list: ' + list_description + '\nFields per item: ' + str(fields) + '\n' + limit_note + '\n\nPage URL: ' + page_url + '\nPage content:\n' + page_text[:15000]}],
        max_tokens=3000,
    )
    extracted = _clean_json(extract_raw) or {}
    page_title_final = extracted.get('page_title') or page_title
    list_title = extracted.get('list_title') or list_description
    items = extracted.get('items') or []
    if not isinstance(items, list):
        items = []
    if limit > 0:
        items = items[:limit]
    log.append('Extracted ' + str(len(items)) + ' items')

    def _has_link(it):
        if not isinstance(it, dict):
            return True
        return bool((it.get('link') or it.get('url') or '').strip())

    missing = [it for it in items if isinstance(it, dict) and not _has_link(it)]
    if missing:
        log.append('Attempting link recovery for ' + str(len(missing)) + ' items')
        for it in items:
            if not isinstance(it, dict) or _has_link(it):
                continue
            topic = it.get('topic') or it.get('title') or it.get('name') or ''
            if not topic:
                continue
            try:
                lr = search_serper(str(page_title_final) + ' ' + str(topic) + ' lecture slides video', topk=6)
            except Exception as e:
                log.append('Link search failed for ' + str(topic) + ': ' + str(e))
                continue
            if not lr or (isinstance(lr, list) and 'error' in lr[0]):
                continue
            cand_lines = '\n'.join('[' + str(i) + '] ' + str(r.get('title','')) + ' | ' + str(r.get('link','')) + ' | ' + str(r.get('snippet',''))[:120] for i, r in enumerate(lr))
            pick_raw = call_llm(
                system='You pick the best URL for a specific lecture/topic. Return ONLY JSON with index (int) and url (string). If none is a good match return index -1.',
                messages=[{'role': 'user', 'content': 'Page: ' + page_url + '\nTopic to find link for: ' + str(topic) + '\n\nCandidates:\n' + cand_lines}],
                max_tokens=200,
            )
            pick = _clean_json(pick_raw) or {}
            url_pick = pick.get('url') or ''
            idx_pick = pick.get('index', -1)
            if not url_pick and isinstance(idx_pick, int) and 0 <= idx_pick < len(lr):
                url_pick = lr[idx_pick].get('link', '')
            if url_pick:
                it['link'] = url_pick
                log.append('Recovered link for ' + str(topic) + ': ' + str(url_pick))

    for it in items:
        if isinstance(it, dict) and not _has_link(it):
            it['link'] = page_url
    log.append('Link recovery pass complete')

    md = []
    md.append('# ' + str(page_title_final) + '\n')
    md.append('**Source Page:** ' + page_url + '\n')
    md.append('**List:** ' + str(list_title) + '\n')
    md.append('**Task:** ' + query + '\n')
    md.append('\n## Items\n')
    if items:
        for i, it in enumerate(items, 1):
            if isinstance(it, dict):
                topic = it.get('topic') or it.get('title') or it.get('name') or ''
                link = it.get('link') or it.get('url') or ''
                parts = []
                if topic:
                    parts.append('**' + str(topic) + '**')
                if link:
                    parts.append('[' + str(link) + '](' + str(link) + ')')
                others = []
                for k, v in it.items():
                    if k in ('topic','title','name','link','url'):
                        continue
                    if v:
                        others.append(str(k) + ': ' + str(v))
                line = str(i) + '. ' + ' - '.join(parts)
                if others:
                    line += ' (' + '; '.join(others) + ')'
                md.append(line)
            else:
                md.append(str(i) + '. ' + str(it))
        md.append('')
        md.append('\n## Table\n')
        md.append('| # | Topic | Link |')
        md.append('|---|-------|------|')
        for i, it in enumerate(items, 1):
            if isinstance(it, dict):
                topic = it.get('topic') or it.get('title') or it.get('name') or ''
                link = it.get('link') or it.get('url') or ''
                md.append('| ' + str(i) + ' | ' + str(topic).replace('|','/') + ' | ' + str(link) + ' |')
            else:
                md.append('| ' + str(i) + ' | ' + str(it).replace('|','/') + ' | |')
    else:
        md.append('_No items extracted._')
    md_text = '\n'.join(md)
    with open(output_file, 'w') as f:
        f.write(md_text)
    log.append('Wrote markdown to ' + output_file)

    answer = 'Extracted ' + str(len(items)) + ' items (' + list_description + ') from ' + page_url + ' and saved to ' + output_file + '.'

    summary = call_llm(
        system='You are a research summarizer. Write a detailed SUMMARY (100-2000 words) tracing what was searched, which page was opened, what list was extracted, and how the markdown was produced.',
        messages=[{'role': 'user', 'content': 'Task: ' + query + '\nLog:\n' + '\n'.join(log) + '\n\nPage: ' + page_url + '\nFirst items: ' + json.dumps(items[:5]) + '\nMarkdown file: ' + output_file}],
        max_tokens=2000,
    )

    return {'answer': answer, 'summary': summary}
