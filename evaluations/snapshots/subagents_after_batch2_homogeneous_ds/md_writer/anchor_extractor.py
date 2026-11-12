import os, json, re, tools
from llm import call_llm
from playwright.sync_api import sync_playwright


PROJECT_ROOT = os.path.dirname(os.path.abspath(tools.__file__))
USER_DATA_DIR = os.path.join(PROJECT_ROOT, ".browser_profile")


def main(query: str) -> dict:
    # Ask LLM for the target URL and what list to look for
    plan_raw = call_llm(
        system=(
            'Extract from the user query the exact web page URL to open and a description of the list/section of interest. '
            'Return ONLY JSON with keys: url (string, must start with http), goal (short description).'
        ),
        messages=[{'role': 'user', 'content': query}],
        max_tokens=300,
    )
    try:
        m = re.search(r'\{.*\}', plan_raw, re.DOTALL)
        plan = json.loads(m.group(0)) if m else {}
    except Exception:
        plan = {}
    url = plan.get('url', '')
    goal = plan.get('goal', query)
    if not url.startswith('http'):
        return {'answer': 'No valid URL provided.', 'summary': 'Could not parse URL from query.'}

    anchors = []
    body_text = ''
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            USER_DATA_DIR, headless=True, locale='en-US',
            viewport={'width': 1280, 'height': 900},
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage'],
        )
        page = context.new_page()
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=45000)
            page.wait_for_timeout(3000)
            try:
                page.wait_for_load_state('networkidle', timeout=10000)
            except Exception:
                pass
            # scroll to load lazy content
            for _ in range(4):
                page.mouse.wheel(0, 1200)
                page.wait_for_timeout(600)
            page.mouse.wheel(0, -10000)
            page.wait_for_timeout(500)
            anchors = page.evaluate("""() => {
                const out = [];
                document.querySelectorAll('a[href]').forEach(a => {
                    let t = (a.innerText || a.textContent || '').trim().replace(/\\s+/g,' ');
                    const h = a.href;
                    if (h) out.push({text: t.slice(0,200), href: h});
                });
                return out;
            }""")
            body_text = page.evaluate("() => document.body.innerText")
            current_url = page.url
        except Exception as e:
            context.close()
            return {'answer': 'Failed to load page: ' + str(e), 'summary': 'Playwright navigation error: ' + str(e)}
        context.close()

    # Use LLM to interpret which anchors correspond to the requested list items
    anchor_lines = '\n'.join('[' + str(i) + '] text=' + a['text'] + ' | href=' + a['href'] for i, a in enumerate(anchors))
    extract_raw = call_llm(
        system=(
            'You are given a list of all hyperlinks (text + href) from a web page and the page visible text. '
            'Identify the ordered list the user wants (e.g. lectures, chapters). For each item give its title/topic and the '
            'best matching href (exact from the provided anchors, resolved absolute URL; empty string if truly none). '
            'Return ONLY JSON: {items: [{topic, link}], note: short}. Only use items present on the page. Keep page order.'
        ),
        messages=[{'role': 'user', 'content': 'Goal: ' + goal + '\n\nAnchors:\n' + anchor_lines[:18000] + '\n\nPage visible text (excerpt):\n' + body_text[:6000]}],
        max_tokens=3000,
    )
    try:
        m = re.search(r'\{.*\}', extract_raw, re.DOTALL)
        extracted = json.loads(m.group(0)) if m else {}
    except Exception:
        extracted = {}
    items = extracted.get('items', []) or []

    result_dump = {'url': url, 'goal': goal, 'num_anchors': len(anchors), 'items': items, 'sample_anchors': anchors[:60]}
    with open('anchors_debug.json', 'w') as f:
        json.dump(result_dump, f, indent=2, ensure_ascii=False)

    # Also write a markdown list for convenience
    md = ['# Anchors found on ' + url + '\n']
    md.append('Goal: ' + goal + '\n')
    md.append('## Extracted items\n')
    for i, it in enumerate(items, 1):
        md.append(str(i) + '. ' + str(it.get('topic','')) + ' -- ' + str(it.get('link','')))
    open('anchors_extract.md', 'w').write('\n'.join(md))

    summary = call_llm(
        system='Write a detailed SUMMARY (100-1000 words) of what page was opened, how many anchors were found, and what list items were extracted with links.',
        messages=[{'role': 'user', 'content': 'URL: ' + url + '\nGoal: ' + goal + '\nNum anchors: ' + str(len(anchors)) + '\nExtracted items JSON: ' + json.dumps(items)[:3000] + '\nSample anchors: ' + json.dumps(anchors[:30])[:2000]}],
        max_tokens=1500,
    )
    return {'answer': 'Extracted ' + str(len(items)) + ' items with links from ' + url + '.', 'summary': summary}
