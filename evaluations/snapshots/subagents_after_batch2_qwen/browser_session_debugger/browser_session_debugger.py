import os, glob, json
from playwright.sync_api import sync_playwright
from llm import call_llm
import tools

PROJECT_ROOT = os.path.dirname(os.path.abspath(tools.__file__))

def main(query: str) -> dict:
    evidence = []
    # Discover all possible browser profile dirs
    candidates = []
    for pat in [os.path.join(PROJECT_ROOT, '.browser_profile'),
                os.path.join(PROJECT_ROOT, '.browser_profile*'),
                os.path.join(os.getcwd(), '.browser_profile*'),
                os.path.expanduser('~/.browser_profile*')]:
        for d in glob.glob(pat):
            if os.path.isdir(d):
                candidates.append(d)
    candidates = sorted(set(candidates))
    evidence.append(f"PROJECT_ROOT={PROJECT_ROOT}")
    evidence.append(f"Profile candidates: {candidates}")
    for d in candidates:
        try:
            entries = os.listdir(d)
            evidence.append(f"{d} -> {entries[:20]}")
            # check cookies/login data present
            for sub in ['Default', 'Cookies', 'Network']:
                p = os.path.join(d, sub)
                if os.path.exists(p):
                    evidence.append(f"  contains {sub}")
        except Exception as e:
            evidence.append(f"{d} list error {e}")

    results = {}
    for d in candidates:
        try:
            with sync_playwright() as p:
                ctx = p.chromium.launch_persistent_context(
                    d, headless=True, locale='zh-CN',
                    viewport={'width': 1280, 'height': 800},
                    args=['--disable-blink-features=AutomationControlled','--no-sandbox','--disable-dev-shm-usage'])
                page = ctx.new_page()
                page.goto('https://meeting.tencent.com/', wait_until='domcontentloaded', timeout=30000)
                page.wait_for_timeout(4000)
                url = page.url
                text = ''
                try:
                    text = page.evaluate('() => document.body.innerText')[:1200]
                except Exception:
                    pass
                # cookies count
                cookies = ctx.cookies()
                tencent = [c['name'] for c in cookies if 'tencent' in c.get('domain','') or 'qq' in c.get('domain','')]
                evidence.append(f"PROFILE {d}: url={url} cookies={len(cookies)} tencent_cookies={tencent[:15]}")
                evidence.append(f"  text: {text[:500]}")
                results[d] = {'url': url, 'cookies': len(cookies), 'tencent': tencent}
                ctx.close()
        except Exception as e:
            evidence.append(f"PROFILE {d}: launch error {e}")

    summary = call_llm(
        system="Summarize the browser session diagnostic findings concisely: is the user logged in to Tencent Meeting in any profile? Which profile path appears logged in?",
        messages=[{'role': 'user', 'content': 'Query: ' + query + '\nEvidence:\n' + '\n'.join(evidence)}],
        max_tokens=1500)
    return {'answer': json.dumps(results, ensure_ascii=False), 'summary': summary}
