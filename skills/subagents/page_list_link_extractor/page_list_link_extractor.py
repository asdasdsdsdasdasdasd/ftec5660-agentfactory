import json
import re
import os
from llm import call_llm
from tools import search_serper, read_url_jina


def _clean_json(text):
    t = (text or '').strip()
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


def _try_fetch_jina(url):
    try:
        content = read_url_jina(url)
    except Exception as e:
        return '', str(e)
    if isinstance(content, dict):
        if 'error' in content:
            return '', str(content.get('error'))
        return content.get('text', '') or '', None
    return content or '', None


def _extract_links_playwright(url, max_wait=6000):
    from playwright.sync_api import sync_playwright
    import tools as _tools
    project_root = os.path.dirname(os.path.abspath(_tools.__file__))
    user_data = os.path.join(project_root, '.browser_profile')
    anchors = []
    page_text = ''
    err = None
    try:
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data, headless=True, viewport={'width': 1280, 'height': 900},
                args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage'],
            )
            page = context.new_page()
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(max_wait)
            for _ in range(4):
                page.mouse.wheel(0, 1200)
                page.wait_for_timeout(500)
            data = page.evaluate(
                "() => { const out=[]; document.querySelectorAll('a[href]').forEach(a => { const t=(a.innerText||a.textContent||'').trim().slice(0,200); const h=a.href; if(t||h) out.push({text:t,href:h}); }); return {anchors:out, body:(document.body?document.body.innerText:'').slice(0,20000)}; }"
            )
            anchors = data.get('anchors', [])
            page_text = data.get('body', '')
            context.close()
    except Exception as e:
        err = str(e)
    return anchors, page_text, err


def main(query: str) -> dict:
    log = []
    plan_raw = call_llm(
        system=(
            "You are a web research planner. Given a task, output ONLY JSON with keys: "
            "'search_queries' (2-4 web search queries to locate the exact target page; include a site: query if a domain is implied), "
            "'preferred_site' (domain substring if a specific site is requested, else ''), "
            "'target_page' (short description of the exact page to open), "
            "'items_to_extract' (the list of items required, e.g. 'first 5 lectures'), "
            "'output_file' (a markdown filename ending .md). Return ONLY valid JSON."
        ),
        messages=[{'role': 'user', 'content': 'Task: ' + query}],
        max_tokens=900,
    )
    plan = _clean_json(plan_raw) or {}
    search_queries = plan.get('search_queries') or [query]
    preferred = (plan.get('preferred_site') or '').strip().lower()
    target_page = plan.get('target_page', query)
    items = plan.get('items_to_extract', 'the requested list items')
    output_file = plan.get('output_file') or 'results.md'
    if not output_file.endswith('.md'):
        output_file += '.md'
    log.append('Planned queries: ' + str(search_queries) + ' | preferred: ' + preferred + ' | items: ' + items)

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
        log.append('Search ' + q + ' -> ' + str(len(results)) + ' results')

    def pref_rank(c):
        link = (c.get('link') or '').lower()
        return 0 if (preferred and preferred in link) else 1
    candidates.sort(key=pref_rank)
    shortlist = candidates[:10]
    listing = '\n'.join('[' + str(i) + '] ' + str(c.get('title','')) + ' | ' + str(c.get('link','')) + ' | ' + str(c.get('snippet',''))[:150] for i, c in enumerate(shortlist))
    rank_raw = call_llm(
        system="You choose the single BEST web page to open for the task. Return ONLY JSON: {\"index\": <int>, \"reason\": \"<short>\"}.",
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

    order = [best_idx] + [i for i in range(len(shortlist)) if i != best_idx]
    anchors = []
    page_text = ''
    page_url = ''
    for idx in order:
        c = shortlist[idx]
        url = c.get('link')
        if not url:
            continue
        a, t, err = _extract_links_playwright(url)
        log.append('Playwright ' + url + ' -> anchors=' + str(len(a)) + ' textlen=' + str(len(t)) + ' err=' + str(err))
        if a and len(a) > 3:
            anchors = a
            page_text = t
            page_url = url
            break
        jt, jerr = _try_fetch_jina(url)
        if not jerr and jt and len(jt) > 200:
            page_text = jt
            page_url = url
            log.append('Jina fallback fetched ' + url + ' (' + str(len(jt)) + ' chars)')
            break

    if not page_url:
        summary = call_llm(
            system='Write a SUMMARY of the failed research attempt.',
            messages=[{'role': 'user', 'content': 'Task: ' + query + '\nLog:\n' + '\n'.join(log)}],
            max_tokens=800,
        )
        return {'answer': 'Failed to fetch a suitable page.', 'summary': summary}

    link_lines = []
    for a in anchors[:300]:
        txt = (a.get('text') or '').strip()
        href = a.get('href') or ''
        if len(txt) > 120:
            txt = txt[:120]
        link_lines.append('TEXT: ' + txt + ' || HREF: ' + href)
    links_blob = '\n'.join(link_lines)

    extract_raw = call_llm(
        system=(
            "You are an expert at reading a course syllabus / lecture list page. Using the page text AND the anchor links provided, "
            "identify each requested item (e.g. the first N lectures). For EACH item return its number/title/topic AND the most relevant URL "
            "(choose from the HREF values provided; if an item has a play/notes/pdf link pick the primary one; if no specific link exists, use the page URL). "
            "Output ONLY a JSON object with keys: 'page_title' (string), 'items' (list of objects each with 'number' string, 'topic' string, 'link' string). "
            "Resolve relative info using the given HREFs (they are already absolute). Do NOT invent URLs not present in the links. Return ONLY valid JSON."
        ),
        messages=[{'role': 'user', 'content': 'Task: ' + query + '\nItems required: ' + items + '\nPage URL: ' + page_url + '\n\n=== PAGE TEXT (may be partial) ===\n' + page_text[:6000] + '\n\n=== ANCHOR LINKS ===\n' + links_blob[:12000]}],
        max_tokens=2500,
    )
    extracted = _clean_json(extract_raw) or {}
    page_title = extracted.get('page_title') or 'Course Page'
    item_list = extracted.get('items') or []
    log.append('Extracted ' + str(len(item_list)) + ' items')

    md = []
    md.append('# ' + str(page_title) + '\n')
    md.append('**Source:** ' + page_url + '\n')
    md.append('**Task:** ' + query + '\n')
    md.append('## Requested Items\n')
    md.append('| # | Topic | Link |')
    md.append('|---|-------|------|')
    for it in item_list:
        num = str(it.get('number', '')).replace('|', '/')
        topic = str(it.get('topic', '')).replace('|', '/')
        link = str(it.get('link', ''))
        md.append('| ' + num + ' | ' + topic + ' | ' + link + ' |')
    md.append('')
    md_text = '\n'.join(md)
    with open(output_file, 'w') as f:
        f.write(md_text)
    log.append('Wrote markdown to ' + output_file)

    summary = call_llm(
        system='You are a research summarizer. Write a detailed SUMMARY (100-2000 words) tracing what was searched, which page was opened, what anchors were found, what was extracted, any limitations, and how markdown was produced.',
        messages=[{'role': 'user', 'content': 'Task: ' + query + '\nLog:\n' + '\n'.join(log) + '\n\nPage: ' + page_url + '\nExtracted items JSON: ' + json.dumps(item_list)[:2000] + '\nMarkdown file: ' + output_file}],
        max_tokens=2000,
    )

    ans_items = '; '.join(str(it.get('number','')) + ': ' + str(it.get('topic','')) + ' -> ' + str(it.get('link','')) for it in item_list)
    answer = 'Saved ' + str(len(item_list)) + ' items to ' + output_file + '. Items: ' + ans_items[:800]
    return {'answer': answer, 'summary': summary}
