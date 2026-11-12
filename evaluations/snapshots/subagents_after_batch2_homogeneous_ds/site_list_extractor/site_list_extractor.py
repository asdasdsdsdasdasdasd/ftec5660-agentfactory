import os, re, json
from llm import call_llm
import tools
from tools import search_serper, read_url_jina

PROJECT_ROOT = os.path.dirname(os.path.abspath(tools.__file__))
USER_DATA_DIR = os.path.join(PROJECT_ROOT, ".browser_profile")


def _extract_json(text):
    if not text:
        return None
    depth = 0; start = None
    for i, c in enumerate(text):
        if c == '{':
            if depth == 0: start = i
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    return json.loads(text[start:i+1])
                except Exception:
                    start = None
    return None


def plan(query):
    sys = ("You parse a user's web-research request into structured JSON. "
           "Return ONLY JSON with keys: search_query (string, concise Google search to find the target page), "
           "page_hints (list of strings likely appearing in URL/title of target page), "
           "item_count (integer, how many items to extract; default 5), "
           "item_type (string, e.g. 'lectures', 'courses', 'table rows'), "
           "output_filename (a .md filename derived from request).")
    resp = call_llm(sys, [{"role": "user", "content": query}], max_tokens=400)
    d = _extract_json(resp) or {}
    d.setdefault('search_query', query)
    d.setdefault('page_hints', [])
    d.setdefault('item_count', 5)
    d.setdefault('item_type', 'items')
    d.setdefault('output_filename', 'extracted_results.md')
    if not str(d['output_filename']).endswith('.md'):
        d['output_filename'] = str(d['output_filename']) + '.md'
    return d


def find_url(plan_d):
    results = search_serper(plan_d['search_query'], topk=10)
    clean = [r for r in results if 'error' not in r]
    listing = json.dumps(clean, ensure_ascii=False, indent=1)
    sys = ("You choose the single best URL for a user's target page from search results. "
           "Prefer official/canonical pages matching the hints. Return ONLY JSON: {\"url\": \"...\", \"reason\": \"...\"}")
    user = f"Target hints: {plan_d['page_hints']}\nItem type: {plan_d['item_type']}\nSearch results:\n{listing}"
    resp = call_llm(sys, [{"role": "user", "content": user}], max_tokens=300)
    d = _extract_json(resp) or {}
    url = d.get('url')
    if not url and clean:
        url = clean[0].get('link')
    return url, clean


def _js_collect_anchors():
    return """() => {
        const out = [];
        const seen = new Set();
        document.querySelectorAll('a[href]').forEach(a => {
            const text = (a.innerText || a.textContent || '').trim().replace(/\\s+/g,' ');
            if (!text) return;
            let href = a.href || '';
            if (!href) return;
            const key = text + '||' + href;
            if (seen.has(key)) return;
            seen.add(key);
            out.push({text: text.slice(0,200), href: href});
        });
        const tables = [];
        document.querySelectorAll('table').forEach((t) => {
            const rows = [];
            t.querySelectorAll('tr').forEach(tr => {
                const cells = [];
                tr.querySelectorAll('th,td').forEach(td => {
                    const link = td.querySelector('a[href]');
                    cells.push({text:(td.innerText||'').trim().replace(/\\s+/g,' ').slice(0,300), href: link ? link.href : null});
                });
                if (cells.length) rows.push(cells);
            });
            if (rows.length) tables.push(rows);
        });
        return {title: document.title, url: location.href, anchors: out, tables: tables};
    }"""


def scrape(url):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            USER_DATA_DIR, headless=True, viewport={"width": 1280, "height": 1600},
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(3000)
            data = page.evaluate(_js_collect_anchors())
        finally:
            context.close()
    return data


def select_items(plan_d, url, page_data, extra_text):
    anchors = page_data.get('anchors', [])
    tables = page_data.get('tables', [])
    n = int(plan_d['item_count'])
    sys = ("You select a structured ordered list of items WITH their links from scraped page data. "
           f"The user wants the first {n} '{plan_d['item_type']}'. "
           "Identify the contiguous ordered list representing these items (e.g. lecture list, schedule, syllabus). "
           "Ignore navigation/menu/footer/social links. Resolve relative links to absolute using the page URL. "
           "If a topic item has no direct link but is part of a detail page, still include it with the best available link (or empty). "
           "Return ONLY JSON: {\"items\": [{\"index\": 1, \"topic\": \"...\", \"link\": \"absolute url or empty\"}], \"note\": \"...\"}"
           f" Return exactly up to {n} items IN ORDER. If a topic has no direct link, set link to \"\".")
    payload = {
        "page_url": url,
        "page_title": page_data.get('title'),
        "anchors": anchors[:500],
        "tables": tables[:20],
        "page_text_excerpt": extra_text[:5000],
        "item_count": n,
        "item_type": plan_d['item_type'],
    }
    user = json.dumps(payload, ensure_ascii=False)
    resp = call_llm(sys, [{"role": "user", "content": user}], max_tokens=1500)
    d = _extract_json(resp) or {}
    items = d.get('items', [])
    if not items:
        cand = [a for a in anchors if len(a['text']) > 3]
        items = [{"index": i+1, "topic": c['text'], "link": c['href']} for i, c in enumerate(cand[:n])]
    out = []
    for i, it in enumerate(items[:n]):
        out.append({
            "index": it.get('index', i+1),
            "topic": str(it.get('topic', '')).strip(),
            "link": str(it.get('link', '') or '').strip(),
        })
    return out, d.get('note', '')


def main(query: str) -> dict:
    trace = []
    plan_d = plan(query)
    trace.append(f"PLAN: {json.dumps(plan_d, ensure_ascii=False)}")

    url, search_clean = find_url(plan_d)
    trace.append(f"CHOSEN URL: {url}")
    if not url:
        return {"answer": "Could not determine a target URL from search.", "summary": "\n".join(trace)}

    extra_text = ""
    try:
        doc = read_url_jina(url)
        if isinstance(doc, str):
            extra_text = doc
        elif isinstance(doc, dict):
            extra_text = doc.get('text', '') or doc.get('content', '') or ''
    except Exception as e:
        trace.append(f"read_url_jina failed: {e}")
    if extra_text:
        trace.append(f"Fetched page text ({len(extra_text)} chars) via read_url_jina.")

    page_data = {}
    try:
        page_data = scrape(url)
        trace.append(f"Scraped via Playwright: {len(page_data.get('anchors', []))} anchors, {len(page_data.get('tables', []))} tables.")
    except Exception as e:
        trace.append(f"Playwright scrape failed: {e}. Relying on text fetch.")
        page_data = {"title": "", "url": url, "anchors": [], "tables": []}

    items, note = select_items(plan_d, url, page_data, extra_text)
    trace.append(f"SELECTED {len(items)} items. note={note}")

    lines = []
    lines.append(f"# {plan_d['item_type'].title()} — Extracted from {url}\n")
    lines.append(f"**Source URL:** {url}  ")
    lines.append(f"**Page title:** {page_data.get('title','')}  ")
    lines.append(f"**Query:** {query}\n")
    lines.append("| # | Topic | Link |")
    lines.append("|---|-------|------|")
    for it in items:
        topic = it['topic'].replace('|', '\\|')
        link = it['link']
        link_md = f"[{link}]({link})" if link else "(none / on page)"
        lines.append(f"| {it['index']} | {topic} | {link_md} |")
    lines.append("")
    md = "\n".join(lines)

    out_path = plan_d['output_filename']
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(md)
    trace.append(f"Wrote markdown to {out_path}")

    answer = f"Extracted {len(items)} '{plan_d['item_type']}' from {url} and saved to {plan_d['output_filename']}.\n" + md

    summary = call_llm(
        "You are a research summarizer. Write a detailed SUMMARY (100-2000 words) of the extraction process: what was searched, the URL chosen, how items were identified, what evidence was used, and how results were saved.",
        [{"role": "user", "content": f"Query: {query}\nTrace:\n{chr(10).join(trace)}\nFinal items: {json.dumps(items, ensure_ascii=False)}\nOutput file: {out_path}"}],
        max_tokens=800,
    )
    return {"answer": answer, "summary": summary}
