import os, json
import tools
from playwright.sync_api import sync_playwright
from llm import call_llm

PROJECT_ROOT = os.path.dirname(os.path.abspath(tools.__file__))
USER_DATA_DIR = os.path.join(PROJECT_ROOT, ".browser_profile")


def audio_probe(page):
    return page.evaluate("""() => {
        const out = {audio:[], iframes:[]};
        document.querySelectorAll('audio, video').forEach(a => {
            out.audio.push({tag:a.tagName, src:(a.currentSrc||a.src||'').slice(0,80), paused:a.paused, ct:a.currentTime, dur:a.duration, readyState:a.readyState});
        });
        document.querySelectorAll('iframe').forEach(f=>out.iframes.push((f.src||'').slice(0,80)));
        // look for known player framework globals
        out.imgs = document.images ? 'yes' : 'no';
        return out;
    }""")


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
        evidence.append(f"Initial audio probe: {json.dumps(audio_probe(page))}")
        # Find play buttons: text '播放', aria-labels, classes with play
        info = page.evaluate("""() => {
            const res=[];
            document.querySelectorAll('*').forEach(el=>{
                const t=(el.innerText||'').trim();
                const cls=(el.className||'').toString();
                const al=el.getAttribute&&el.getAttribute('aria-label')||'';
                if(t==='播放' || /play/i.test(cls) || /播放/.test(al)){
                    const r=el.getBoundingClientRect();
                    if(r.width>0&&r.height>0) res.push({tag:el.tagName, text:t.slice(0,20), cls:cls.slice(0,60), aria:al, x:Math.round(r.x),y:Math.round(r.y),w:Math.round(r.width),h:Math.round(r.height)});
                }
            });
            return res.slice(0,30);
        }""")
        evidence.append(f"Play candidates: {json.dumps(info, ensure_ascii=False)}")
        # Try clicking the first visible '播放' element
        clicked = page.evaluate("""() => {
            const els=[...document.querySelectorAll('*')];
            for(const el of els){
                const t=(el.innerText||'').trim();
                if(t==='播放'){
                    const r=el.getBoundingClientRect();
                    if(r.width>0&&r.height>0){ el.click(); return 'clicked-exact'; }
                }
            }
            return 'not-found';
        }""")
        evidence.append(f"Click attempt: {clicked}")
        page.wait_for_timeout(4000)
        evidence.append(f"Post-click audio probe: {json.dumps(audio_probe(page))}")
        # also inspect global player state
        pstate = page.evaluate("""() => {
            const keys=[];
            for(const k of Object.keys(window)){ if(/player|music|audio|Player|Music/i.test(k)) keys.push(k); }
            let detail={};
            try{ if(window.player) detail.playerType=typeof window.player; }catch(e){}
            return {globals:keys.slice(0,20)};
        }""")
        evidence.append(f"Global player keys: {json.dumps(pstate, ensure_ascii=False)}")
        ctx.close()
    summary = call_llm(
        system="Diagnose how QQ Music plays audio and whether clicking play worked. Report concrete findings on audio elements, play button clicks, and player state.",
        messages=[{"role": "user", "content": "Task: " + query + "\nEvidence:\n" + "\n".join(evidence)}],
        max_tokens=1500,
    )
    return {"answer": "\n".join(evidence)[:3500], "summary": summary}
