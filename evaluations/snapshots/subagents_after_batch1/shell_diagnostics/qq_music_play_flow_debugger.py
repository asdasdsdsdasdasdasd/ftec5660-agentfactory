import os, json, re
import tools
from playwright.sync_api import sync_playwright
from llm import call_llm

PROJECT_ROOT = os.path.dirname(os.path.abspath(tools.__file__))
USER_DATA_DIR = os.path.join(PROJECT_ROOT, ".browser_profile")


def main(query: str) -> dict:
    evidence = []
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    network = []
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            USER_DATA_DIR, headless=False, locale="zh-CN",
            viewport={"width": 1280, "height": 800},
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage", "--autoplay-policy=no-user-gesture-required", "--mute-audio"],
        )
        ctx.on("request", lambda r: network.append(r.url) if re.search(r'(song|music|url|vkey|stream|\.mp3|\.m4a|getplaysong|fcg)', r.url, re.I) else None)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        # Go to song detail page directly
        page.goto("https://y.qq.com/n/ryqq/songDetail/003hvIkL1QiILk", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(4000)
        title = page.title()
        body = page.evaluate("() => document.body.innerText")[:300]
        evidence.append(f"Song detail URL: {page.url}\nTitle: {title}\nBody: {body}")

        # Find play buttons on detail page
        btns = page.evaluate("""() => {
            const out=[];
            document.querySelectorAll('a,button,div,span,i').forEach(el=>{
                const t=(el.innerText||'').trim();
                const cls=(el.className||'').toString();
                const al=(el.getAttribute&&el.getAttribute('aria-label'))||'';
                if(t==='播放' || t==='立即播放' || /btn.*play|play.*btn|mod_btn_play/i.test(cls) || /play/i.test(al)){
                    const r=el.getBoundingClientRect();
                    if(r.width>0&&r.height>0) out.push({tag:el.tagName,text:t.slice(0,10),cls:cls.slice(0,50),x:Math.round(r.x),y:Math.round(r.y)});
                }
            });
            return out.slice(0,15);
        }""")
        evidence.append(f"Play buttons on detail: {json.dumps(btns, ensure_ascii=False)}")

        # Click the first play button (native)
        clicked = page.evaluate("""() => {
            const els=[...document.querySelectorAll('a,button,div,span')];
            for(const el of els){
                const t=(el.innerText||'').trim();
                if((t==='播放'||t==='立即播放')){ const r=el.getBoundingClientRect(); if(r.width>0&&r.height>0){ el.click(); return 'clicked:'+t; } }
            }
            return 'none';
        }""")
        evidence.append(f"Clicked: {clicked}")
        page.wait_for_timeout(5000)

        # Playback detection: check all frames for audio
        def scan_audio(pg):
            arr = []
            for fr in pg.frames:
                try:
                    a = fr.evaluate("""() => {
                        const out=[]; document.querySelectorAll('audio,video').forEach(x=>out.push({paused:x.paused,ct:x.currentTime,dur:x.duration,src:(x.currentSrc||x.src||'').slice(0,50)}));
                        return out;
                    }""")
                    if a: arr.extend(a)
                except Exception: pass
            return arr
        audio = scan_audio(page)
        evidence.append(f"Audio elements (all frames) after click: {json.dumps(audio)}")

        # Time indicator check on player footer if present
        for sel in ['.player_music__time', '.song_name__time', '.mod_songname .time', '.player__songname .time']:
            try:
                t = page.eval_on_selector(sel, 'e=>e.innerText')
                evidence.append(f"Time [{sel}]: {t}")
            except Exception:
                pass
        # global player object
        gstate = page.evaluate("""() => {
            const r={};
            try { if (window.player && window.player.getPlayerState) r.playerState = window.player.getPlayerState(); } catch(e){}
            try { if (window.player) r.hasPlayer = true; } catch(e){}
            return r;
        }""")
        evidence.append(f"Global player: {json.dumps(gstate, ensure_ascii=False)}")
        page.wait_for_timeout(3000)
        audio2 = scan_audio(page)
        evidence.append(f"Audio elements after +3s: {json.dumps(audio2)}")

        # relevant network requests
        relevant = [u for u in network if re.search(r'(getplaysong|vkey|stream|url|fcg|\.mp3|\.m4a|playsong)', u, re.I)][:15]
        evidence.append(f"Relevant network requests ({len(network)} total): {json.dumps(relevant, ensure_ascii=False)}")
        ctx.close()
    summary = call_llm(
        system="Diagnose whether QQ Music playback started on the song detail page. Report: did a play button exist, was it clicked, did any audio element appear/play, did the time advance, were there streaming network requests. Be concrete.",
        messages=[{"role": "user", "content": "\n".join(evidence)}],
        max_tokens=1500,
    )
    return {"answer": "\n".join(evidence)[:4000], "summary": summary}
