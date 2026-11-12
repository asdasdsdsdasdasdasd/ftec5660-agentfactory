import os, json, re
from playwright.sync_api import sync_playwright
from llm import call_llm
from tools import search_serper
import tools

PROJECT_ROOT = os.path.dirname(os.path.abspath(tools.__file__))
USER_DATA_DIR = os.path.join(PROJECT_ROOT, ".browser_profile")

JS_TAG_ELEMENTS = r"""(startId) => {
    document.querySelectorAll('[data-bid]').forEach(e => e.removeAttribute('data-bid'));
    const sels = 'button, input, textarea, select, a[href], ' +
        '[role="button"], [role="tab"], [role="link"], [role="menuitem"], ' +
        '[role="option"], [role="switch"], [role="textbox"], [role="combobox"], ' +
        '[role="checkbox"], [role="radio"], [contenteditable="true"], ' +
        '[onclick], [tabindex]:not([tabindex="-1"])';
    const candidates = [...document.querySelectorAll(sels)];
    document.querySelectorAll('div, span, li, label, td, img, svg').forEach(el => {
        if (el.matches(sels)) return;
        try { if (window.getComputedStyle(el).cursor === 'pointer') candidates.push(el); } catch(e) {}
    });
    const seen = new Set();
    const results = [];
    let id = startId;
    for (const el of candidates) {
        if (seen.has(el)) continue;
        seen.add(el);
        const rect = el.getBoundingClientRect();
        if (rect.width < 2 || rect.height < 2) continue;
        if (rect.bottom < 0 || rect.top > window.innerHeight) continue;
        if (rect.right < 0 || rect.left > window.innerWidth) continue;
        const style = window.getComputedStyle(el);
        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') continue;
        id++;
        el.setAttribute('data-bid', String(id));
        const text = (el.innerText || '').trim().slice(0, 80);
        const tag = el.tagName.toLowerCase();
        const role = el.getAttribute('role') || '';
        const ariaLabel = el.getAttribute('aria-label') || '';
        const title = el.getAttribute('title') || '';
        const ph = el.getAttribute('placeholder') || '';
        const type = el.getAttribute('type') || '';
        const cls = (el.className || '').toString().slice(0, 80);
        const disabled = el.disabled || el.getAttribute('aria-disabled') === 'true';
        const checked = el.checked === true;
        const ariaSelected = el.getAttribute('aria-selected');
        const ariaExpanded = el.getAttribute('aria-expanded');
        const value = (tag === 'input' || tag === 'textarea') ? (el.value || '').slice(0, 40) : '';
        let desc = '[' + id + '] <' + tag + '>';
        if (role) desc += ' role="' + role + '"';
        if (text) desc += ' "' + text + '"';
        if (ariaLabel && ariaLabel !== text) desc += ' aria="' + ariaLabel + '"';
        if (title && title !== text) desc += ' title="' + title + '"';
        if (ph) desc += ' placeholder="' + ph + '"';
        if (type) desc += ' type="' + type + '"';
        if (cls) desc += ' class="' + cls + '"';
        if (disabled) desc += ' [disabled]';
        if (checked) desc += ' [checked]';
        if (ariaSelected === 'true') desc += ' [selected]';
        if (ariaExpanded !== null) desc += ' expanded=' + ariaExpanded;
        if (value) desc += ' value="' + value + '"';
        desc += ' @(' + Math.round(rect.x) + ',' + Math.round(rect.y) + ',' + Math.round(rect.width) + 'x' + Math.round(rect.height) + ')';
        results.push(desc);
    }
    return JSON.stringify({text: results.join('\n'), nextId: id});
}"""

def get_all_elements(page):
    element_frames = {}
    all_text = []
    next_id = 0
    for i, frame in enumerate(page.frames):
        try:
            raw = frame.evaluate(JS_TAG_ELEMENTS, next_id)
            result = json.loads(raw)
            if result['text']:
                label = "Main Page" if i == 0 else frame.url.split('?')[0][-50:]
                all_text.append(f"-- {label} --\n{result['text']}")
                for bid in range(next_id + 1, result['nextId'] + 1):
                    element_frames[bid] = frame
                next_id = result['nextId']
        except Exception:
            pass
    return "\n".join(all_text), element_frames

def click_element(page, element_frames, bid):
    bid = int(bid)
    frame = element_frames.get(bid, page.main_frame)
    selector = f'[data-bid="{bid}"]'
    el = frame.query_selector(selector)
    if el:
        try:
            el.scroll_into_view_if_needed()
            page.wait_for_timeout(300)
            el.click(force=True)
        except Exception:
            frame.evaluate("""(bid) => {
                const el = document.querySelector(`[data-bid="${bid}"]`);
                if (el) { el.scrollIntoView({block:'center'}); el.click(); }
            }""", str(bid))
    else:
        frame.evaluate("""(bid) => {
            const el = document.querySelector(`[data-bid="${bid}"]`);
            if (el) { el.scrollIntoView({block:'center'}); el.click(); }
        }""", str(bid))
    page.wait_for_timeout(1500)

def type_in_element(page, element_frames, bid, text, clear_first=False):
    bid = int(bid)
    frame = element_frames.get(bid, page.main_frame)
    frame.evaluate("""(bid) => {
        const el = document.querySelector(`[data-bid="${bid}"]`);
        if (el) { el.scrollIntoView({block:'center'}); el.focus(); el.click(); }
    }""", str(bid))
    page.wait_for_timeout(300)
    if clear_first:
        page.keyboard.press("Control+a")
        page.keyboard.press("Delete")
        page.wait_for_timeout(200)
    page.keyboard.type(text, delay=40)
    page.wait_for_timeout(500)

def hover_element(page, element_frames, bid):
    bid = int(bid)
    frame = element_frames.get(bid, page.main_frame)
    el = frame.query_selector(f'[data-bid="{bid}"]')
    if el:
        try:
            el.scroll_into_view_if_needed()
            el.hover()
        except Exception:
            pass
    page.wait_for_timeout(1000)

def select_option(page, element_frames, bid, value):
    bid = int(bid)
    frame = element_frames.get(bid, page.main_frame)
    el = frame.query_selector(f'[data-bid="{bid}"]')
    if el:
        try:
            el.select_option(label=value)
        except Exception:
            try:
                el.select_option(value=value)
            except Exception:
                pass
    page.wait_for_timeout(500)

def find_start_url(query):
    planner = call_llm(
        system="You are a web navigation planner. Given a task to book/create a meeting or event on a web application, produce a search query to find the correct web booking/scheduling entry URL. Reply with ONLY the search query text.",
        messages=[{"role": "user", "content": f"Task: {query}"}],
    )
    search_q = planner.strip().strip('"')
    try:
        results = search_serper(search_q, topk=8)
    except Exception:
        results = []
    candidates = []
    for r in results:
        if isinstance(r, dict) and "error" not in r and r.get("link"):
            candidates.append(f"{r.get('title')} | {r.get('link')} | {r.get('snippet','')[:150]}")
    cand_text = "\n".join(candidates) if candidates else "No candidates"
    pick = call_llm(
        system="You choose the best URL to navigate to for completing a web booking task. Prefer official application URLs (schedule/book/meeting creation pages). Reply with ONLY the single best URL string, nothing else.",
        messages=[{"role": "user", "content": f"Task: {query}\nCandidates:\n{cand_text}"}],
    )
    url = pick.strip().strip('"').strip()
    if not url.startswith("http"):
        url = "https://meeting.tencent.com/"
    return url

def main(query: str) -> dict:
    evidence = []
    final_answer = ""
    start_url = find_start_url(query)
    evidence.append(f"Chosen start URL via search: {start_url}")

    system_prompt = f"""You are an autonomous browser automation agent operating a logged-in web application to complete this task:
TASK: {query}

You control a real Chromium browser. Each step you see the current URL and all interactive elements (with numeric ids, attributes, positions, and state). Elements inside iframes are included.

Reply with ONLY ONE JSON action object (no other text, no markdown):
- {{"action":"click","id":N}}
- {{"action":"type","id":N,"text":"..."}}
- {{"action":"clear_and_type","id":N,"text":"..."}}
- {{"action":"hover","id":N}}
- {{"action":"select","id":N,"value":"..."}}
- {{"action":"press_key","key":"Enter"}}
- {{"action":"scroll","direction":"down"}} (or "up")
- {{"action":"wait","ms":2000}}
- {{"action":"goto","url":"..."}}
- {{"action":"get_text"}}
- {{"action":"done","message":"..."}}  -- ONLY when the task is fully complete. Include the meeting invitation details, meeting ID, and meeting link in the message.

Guidance:
- Discover the booking/scheduling entry from the current page; navigate via UI (menus, buttons) rather than guessing URLs.
- For date/time pickers, read visible options carefully and select the correct date (tomorrow) and time (16:00 / 4 PM). If a time field accepts typing, type it.
- Fill in the topic/title field with the requested topic.
- Click the final confirm/submit/book button to actually create the meeting.
- After creation, extract the meeting ID, invitation details, and meeting link from the success/confirmation page and use them in the "done" message.
- If an element is not found, wait, scroll, or re-query. Adapt if the page differs from expectations."""

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            USER_DATA_DIR, headless=True, locale="zh-CN",
            viewport={"width": 1366, "height": 900},
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"],
        )
        popup_pages = []
        context.on("page", lambda np: popup_pages.append(np))
        page = context.new_page()
        try:
            page.goto(start_url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            evidence.append(f"goto start_url failed: {e}")
        page.wait_for_timeout(3000)
        active_page = page
        messages = []

        for step in range(28):
            if popup_pages:
                try:
                    new_page = popup_pages.pop(0)
                    new_page.wait_for_load_state("domcontentloaded", timeout=8000)
                    new_page.wait_for_timeout(2500)
                    active_page = new_page
                    evidence.append(f"Step {step}: switched to popup {new_page.url}")
                except Exception:
                    pass
            try:
                elements_text, element_frames = get_all_elements(active_page)
            except Exception as e:
                elements_text, element_frames = "", {}
                evidence.append(f"Step {step}: element scan error {e}")
            user_msg = f"Step {step}. URL: {active_page.url}\nElements:\n{elements_text}"
            if len(user_msg) > 45000:
                user_msg = user_msg[:45000] + "\n... (truncated)"
            messages.append({"role": "user", "content": user_msg})
            try:
                response = call_llm(system_prompt, messages[-16:], max_tokens=600)
            except Exception as e:
                evidence.append(f"Step {step}: LLM error {e}")
                break
            messages.append({"role": "assistant", "content": response})
            m = re.search(r'\{[^{}]*\}', response)
            if not m:
                continue
            try:
                action = json.loads(m.group())
            except Exception:
                continue
            act = action.get("action")
            evidence.append(f"Step {step}: {response.strip()[:200]}")
            if act == "done":
                final_answer = action.get("message", "")
                break
            try:
                if act == "click":
                    click_element(active_page, element_frames, action["id"])
                elif act == "type":
                    type_in_element(active_page, element_frames, action["id"], action.get("text", ""))
                elif act == "clear_and_type":
                    type_in_element(active_page, element_frames, action["id"], action.get("text", ""), clear_first=True)
                elif act == "hover":
                    hover_element(active_page, element_frames, action["id"])
                elif act == "select":
                    select_option(active_page, element_frames, action["id"], action.get("value", ""))
                elif act == "press_key":
                    active_page.keyboard.press(action.get("key", "Enter"))
                    active_page.wait_for_timeout(1500)
                elif act == "scroll":
                    dy = 400 if action.get("direction", "down") == "down" else -400
                    active_page.mouse.wheel(0, dy)
                    active_page.wait_for_timeout(1000)
                elif act == "wait":
                    active_page.wait_for_timeout(action.get("ms", 2000))
                elif act == "goto":
                    active_page.goto(action["url"], wait_until="domcontentloaded")
                    active_page.wait_for_timeout(2500)
                elif act == "get_text":
                    txt = active_page.evaluate("() => document.body.innerText")
                    messages.append({"role": "user", "content": f"Page text:\n{txt[:5000]}"})
            except Exception as e:
                messages.append({"role": "user", "content": f"Action '{act}' failed: {e}"})
                evidence.append(f"Step {step}: action error {e}")

        try:
            final_text = active_page.evaluate("() => document.body.innerText")
            evidence.append("FINAL PAGE TEXT:\n" + final_text[:3000])
        except Exception:
            pass
        try:
            context.close()
        except Exception:
            pass

    if not final_answer:
        final_answer = call_llm(
            system="You analyze browser automation evidence. Determine whether the meeting was successfully created and extract the meeting invitation details, meeting ID, and meeting link. Reply concisely with the result, or state clearly that creation did NOT succeed and what blocked it.",
            messages=[{"role": "user", "content": f"Task: {query}\nEvidence:\n" + "\n".join(evidence[-40:])}],
        )

    summary = call_llm(
        system="You are a summarizer. Write a detailed SUMMARY (100-2000 words) of the browser automation attempt: what navigation steps were taken, what was found, and how the outcome was determined.",
        messages=[{"role": "user", "content": f"Task: {query}\nEvidence:\n" + "\n".join(evidence)}],
        max_tokens=3000,
    )
    return {"answer": final_answer, "summary": summary}
