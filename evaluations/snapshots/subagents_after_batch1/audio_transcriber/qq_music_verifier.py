import os, json
import tools
from playwright.sync_api import sync_playwright
from llm import call_llm

PROJECT_ROOT = os.path.dirname(os.path.abspath(tools.__file__))
USER_DATA_DIR = os.path.join(PROJECT_ROOT, ".browser_profile")


def main(query: str) -> dict:
    evidence = []
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    result = {}
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            USER_DATA_DIR, headless=True, locale="zh-CN",
            viewport={"width": 1280, "height": 800},
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto("https://y.qq.com/n/ryqq_v2/player", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(4000)
            url = page.url
            text = page.evaluate("() => document.body.innerText")[:2500]
            audio_state = page.evaluate("""() => {
                const out = [];
                document.querySelectorAll('audio, video').forEach(a => {
                    out.push({tag: a.tagName, src: a.currentSrc||a.src||'', paused: a.paused, currentTime: a.currentTime, duration: a.duration});
                });
                return out;
            }""")
            evidence.append(f"URL: {url}")
            evidence.append(f"Page text:\n{text}")
            evidence.append(f"Audio elements: {json.dumps(audio_state)}")
            result = {"url": url, "audio": audio_state, "text_excerpt": text[:800]}
        except Exception as e:
            evidence.append(f"error: {e}")
        ctx.close()
    summary = call_llm(
        system="Report whether the QQ Music player shows the requested song and whether it is actually playing (based on audio element paused/currentTime). Be concrete.",
        messages=[{"role": "user", "content": "Task: " + query + "\nEvidence:\n" + "\n".join(evidence)}],
        max_tokens=1500,
    )
    return {"answer": json.dumps(result, ensure_ascii=False)[:3000], "summary": summary}
