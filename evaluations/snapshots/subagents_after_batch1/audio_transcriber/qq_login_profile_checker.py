import os, json
from playwright.sync_api import sync_playwright
from llm import call_llm


def check_profile(path):
    res = {"path": path, "login": None, "url": "", "cookies_qq": [], "snippet": "", "error": ""}
    try:
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                path, headless=True, locale="zh-CN",
                viewport={"width": 1280, "height": 800},
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage", "--autoplay-policy=no-user-gesture-required"],
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto("https://y.qq.com/n/ryqq_v2/player", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(4000)
            res["url"] = page.url
            cookies = ctx.cookies()
            qq = [c['name'] for c in cookies if 'qq.com' in c.get('domain','')]
            res["cookies_qq"] = qq[:30]
            # login indicator: presence of avatar/nickname vs login link
            info = page.evaluate("""() => {
                const hasLogin = !!(document.querySelector('.player_login__link') && document.querySelector('.player_login__link').innerText.includes('登录'));
                const nameEl = document.querySelector('.player_login__name, [class*=user_name], [class*=nickname]');
                return {hasLoginLink: hasLogin, name: nameEl ? nameEl.innerText.slice(0,40) : '', bodyStart: document.body.innerText.slice(0,80)};
            }""")
            login_cookie_names = {'uin','qqmusic_key','qm_keyst','p_uin','p_skey','skey','wxuin','wxskey','musickey'}
            has_login_cookie = bool(set(qq) & login_cookie_names)
            res["has_login_link"] = info.get("hasLoginLink")
            res["has_login_cookie"] = has_login_cookie
            res["login"] = (not info.get("hasLoginLink")) and has_login_cookie
            res["snippet"] = info.get("bodyStart", "")
            res["name"] = info.get("name", "")
            ctx.close()
    except Exception as e:
        res["error"] = str(e)
    return res


def main(query: str) -> dict:
    # query = JSON list of profile paths, or discover defaults
    import re
    profiles = []
    try:
        m = re.search(r'\[.*\]', query, re.DOTALL)
        if m:
            profiles = json.loads(m.group(0))
    except Exception:
        pass
    if not profiles:
        profiles = [
            "/mnt/d/openclaw/AgentFactory/.browser_profile",
            "/home/chiwaiwan21/openclaw-browser-profile",
            "/home/chiwaiwan21/.openclaw/browser/openclaw/user-data",
            "/home/chiwaiwan21/snap/chromium/common/openclaw-cdp",
            "/home/chiwaiwan21/snap/chromium/common/chromium",
        ]
    results = []
    for pr in profiles:
        if not os.path.isdir(pr):
            results.append({"path": pr, "error": "does not exist"})
            continue
        results.append(check_profile(pr))
    summary = call_llm(
        system="Report which QQ Music browser profile is logged in (has login link false + login cookies). Give clear per-profile verdict and which path to use.",
        messages=[{"role": "user", "content": json.dumps(results, ensure_ascii=False)[:6000]}],
        max_tokens=1500,
    )
    return {"answer": json.dumps(results, ensure_ascii=False)[:3500], "summary": summary}
