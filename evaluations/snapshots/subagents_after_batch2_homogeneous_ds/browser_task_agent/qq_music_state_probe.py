import os, json, re
import tools
from playwright.sync_api import sync_playwright
from llm import call_llm

PROJECT_ROOT = os.path.dirname(os.path.abspath(tools.__file__))
USER_DATA_DIR = os.path.join(PROJECT_ROOT, ".browser_profile")


def get_time_txt(page):
    try:
        return page.eval_on_selector('.player_music__time', 'el => el.innerText')
    except Exception:
        return 'NO_TIME_ELEM'


def main(query: str) -> dict:
    evidence = []
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            USER_DATA_DIR, headless=True, locale="zh-CN",
            viewport={"width": 1280, "height": 800},
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage", "--autoplay-policy=no-user-gesture-required"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://y.qq.com/n/ryqq_v2/player", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(4000)

        # Login state check
        login_info = page.evaluate("""() => {
            const bodyTxt = document.body.innerText;
            const hasLoginBtn = !!(document.querySelector('.player_login__link') && document.querySelector('.player_login__link').innerText.includes('登录'));
            // Try to read any user nickname element
            const nick = document.querySelector('.player_login__name, .mod_player_login .user_name, [class*=nick]');
            return {hasLoginBtn, nick: nick?nick.innerText.slice(0,30):'', snippet: bodyTxt.slice(0,120)};
        }""")
        evidence.append(f"Login info: {json.dumps(login_info, ensure_ascii=False)}")

        # Cookie check
        cookies = ctx.cookies()
        qq_cookies = [c['name'] for c in cookies if 'qq.com' in c.get('domain','')]
        evidence.append(f"QQ cookies present: {qq_cookies[:25]}")
        logged_in_cookies = [n for n in qq_cookies if n in ('uin','qm_keyst','p_uin','p_skey','skey','qqmusic_key','qm_keyst')]
        evidence.append(f"Login-indicator cookies: {logged_in_cookies}")

        # Before play state
        t_before = get_time_txt(page)
        evidence.append(f"Time before: {t_before}")

        # Native click on big play button
        try:
            btn = page.query_selector('.btn_big_play')
            if btn:
                btn.scroll_into_view_if_needed()
                btn.click(force=True)
                evidence.append("Clicked .btn_big_play via native Playwright click")
            else:
                evidence.append("btn_big_play NOT FOUND")
        except Exception as e:
            evidence.append(f"click error: {e}")

        page.wait_for_timeout(3000)
        t_after1 = get_time_txt(page)
        evidence.append(f"Time after 3s: {t_after1}")
        page.wait_for_timeout(4000)
        t_after2 = get_time_txt(page)
        evidence.append(f"Time after ~7s: {t_after2}")

        # Detect play/pause icon class change on big button
        btn_state = page.evaluate("""() => {
            const b = document.querySelector('.btn_big_play');
            return b ? b.className : 'none';
        }""")
        evidence.append(f"Big play btn class after click: {btn_state}")

        # Check any AudioContext / hidden audio
        audio2 = page.evaluate("""() => {
            const arr=[];
            document.querySelectorAll('audio,video').forEach(a=>arr.push({paused:a.paused,ct:a.currentTime,src:(a.src||'').slice(0,60)}));
            return arr;
        }""")
        evidence.append(f"Audio elements after click: {json.dumps(audio2)}")

        playing = (t_before != t_after2) and t_after2 not in ('NO_TIME_ELEM','00:00 / 03:31') and (t_after1 != t_before or t_after2 != t_before)
        evidence.append(f"DEDUCED PLAYING: {playing} (before={t_before}, after1={t_after1}, after2={t_after2})")
        ctx.close()

    summary = call_llm(
        system="Report concretely: (1) Is the QQ Music browser logged in or not? (2) Did playback start after clicking play, based on the time counter advancing? Give a clear yes/no for each.",
        messages=[{"role": "user", "content": "Evidence:\n" + "\n".join(evidence)}],
        max_tokens=1200,
    )
    return {"answer": "\n".join(evidence)[:3500], "summary": summary}
