import os, json, re, textwrap
import tools
from llm import call_llm
from tools import execute_shell_command

PROJECT_ROOT = os.path.dirname(os.path.abspath(tools.__file__))
USER_DATA_DIR = os.path.join(PROJECT_ROOT, ".browser_profile")
KEEPER = os.path.join(PROJECT_ROOT, "_browser_keeper.py")

# The keeper script runs DETACHED: it launches a persistent, non-headless browser,
# performs the LLM-driven task, then stays alive holding the browser open.
KEEPER_TEMPLATE = r'''
import os, sys, json, re, time
os.environ.setdefault("DISPLAY", ":1")
import tools
from playwright.sync_api import sync_playwright
from llm import call_llm

PROJECT_ROOT = os.path.dirname(os.path.abspath(tools.__file__))
USER_DATA_DIR = os.path.join(PROJECT_ROOT, ".browser_profile")
TASK = __TASK__

JS_TAG_ELEMENTS = r"""(startId) => {
    document.querySelectorAll('[data-bid]').forEach(e => e.removeAttribute('data-bid'));
    const sels = 'button, input, textarea, select, a[href], [role=\"button\"], [role=\"link\"], [role=\"tab\"], [role=\"menuitem\"], [role=\"option\"], [contenteditable=\"true\"], [onclick], [tabindex]:not([tabindex=\"-1\"])';
    const candidates=[...document.querySelectorAll(sels)];
    document.querySelectorAll('div,span,li,label,a,i,img').forEach(el=>{if(el.matches(sels))return;try{if(window.getComputedStyle(el).cursor==='pointer')candidates.push(el);}catch(e){}});
    const seen=new Set();const results=[];let id=startId;
    for(const el of candidates){if(seen.has(el))continue;seen.add(el);const r=el.getBoundingClientRect();if(r.width<2||r.height<2)continue;if(r.bottom<0||r.top>window.innerHeight)continue;const st=window.getComputedStyle(el);if(st.display==='none'||st.visibility==='hidden')continue;id++;el.setAttribute('data-bid',String(id));const t=(el.innerText||'').trim().slice(0,80);const cls=(el.className||'').toString().slice(0,50);const al=el.getAttribute('aria-label')||'';let d='['+id+'] <'+el.tagName.toLowerCase()+'>';if(t)d+=' \"'+t+'\"';if(al&&al!==t)d+=' aria=\"'+al+'\"';if(cls)d+=' cls='+cls;d+=' @('+Math.round(r.x)+','+Math.round(r.y)+')';results.push(d);}
    return JSON.stringify({text:results.join('\n'),nextId:id});
}"""

def get_elements(page):
    ef={};alltx=[];nid=0
    for i,fr in enumerate(page.frames):
        try:
            raw=fr.evaluate(JS_TAG_ELEMENTS,nid);res=json.loads(raw)
            if res['text']:
                alltx.append(('Main' if i==0 else fr.url[-40:])+"\n"+res['text'])
                for b in range(nid+1,res['nextId']+1):ef[b]=fr
                nid=res['nextId']
        except Exception:pass
    return "\n".join(alltx),ef

def click_el(page,ef,bid):
    bid=int(bid);fr=ef.get(bid,page.main_frame);el=fr.query_selector('[data-bid=\"'+str(bid)+'\"]')
    if el:
        try:el.scroll_into_view_if_needed()
        except Exception:pass
        page.wait_for_timeout(300)
        try:el.click(force=True)
        except Exception:fr.evaluate("(b)=>{const e=document.querySelector('[data-bid=\"'+b+'\"]');if(e)e.click();}",str(bid))
    page.wait_for_timeout(1800)

def type_el(page,ef,bid,text,clear=False):
    bid=int(bid);fr=ef.get(bid,page.main_frame)
    fr.evaluate("(b)=>{const e=document.querySelector('[data-bid=\"'+b+'\"]');if(e){e.focus();e.click();}}",str(bid))
    page.wait_for_timeout(300)
    if clear:page.keyboard.press("Control+a");page.keyboard.press("Backspace");page.wait_for_timeout(150)
    page.keyboard.type(text,delay=40);page.wait_for_timeout(400)

result_box={}
with sync_playwright() as p:
    ctx=p.chromium.launch_persistent_context(
        USER_DATA_DIR,headless=False,locale="zh-CN",
        viewport={"width":1280,"height":800},
        args=["--disable-blink-features=AutomationControlled","--no-sandbox","--disable-dev-shm-usage","--autoplay-policy=no-user-gesture-required"],
    )
    popups=[]
    ctx.on("page",lambda pg:popups.append(pg))
    page=ctx.pages[0] if ctx.pages else ctx.new_page()
    start=call_llm(system="Return ONLY the best starting URL to accomplish this web task (a bare URL, nothing else).",messages=[{"role":"user","content":"Task: "+TASK}],max_tokens=120).strip().split()[0]
    if not start.startswith("http"):start="https://y.qq.com"
    try:
        page.goto(start,wait_until="domcontentloaded",timeout=40000);page.wait_for_timeout(3500)
    except Exception as e:
        pass
    sysp=("You are a browser automation agent controlling a REAL non-headless Chromium on QQ Music (y.qq.com), already logged in.\nTASK: "+TASK+"\n\n"
        "Each step shows URL + interactive elements [N]. Reply ONLY one JSON action:\n"
        '{"action":"click","id":N} | {"action":"type","id":N,"text":"..."} | {"action":"clear_and_type","id":N,"text":"..."} | '
        '{"action":"press_key","key":"Enter"} | {"action":"scroll","direction":"down"} | {"action":"wait","ms":2000} | {"action":"goto","url":"..."} | {"action":"get_text"} | {"action":"done","message":"..."}\n'
        "Flow: if a search box exists, type the song + artist, submit; open the matching song; click the play button (播放). When playback appears started, return done.")
    msgs=[];active=page;done_msg=""
    for step in range(28):
        if popups:
            np=popups.pop(0)
            try:np.wait_for_load_state("domcontentloaded",timeout=8000)
            except Exception:pass
            np.wait_for_timeout(2000);active=np
        try:els,ef=get_elements(active)
        except Exception:els,ef="",{}
        um="Step %d. URL: %s\nElements:\n%s"%(step,active.url,els)
        if len(um)>45000:um=um[:45000]
        msgs.append({"role":"user","content":um})
        resp=call_llm(sysp,msgs[-16:],max_tokens=400)
        msgs.append({"role":"assistant","content":resp})
        m=re.search(r'\{[^{}]*\}',resp)
        if not m:continue
        try:a=json.loads(m.group())
        except Exception:continue
        act=a.get("action")
        if act=="done":done_msg=a.get("message","done");break
        try:
            if act=="click":click_el(active,ef,a["id"])
            elif act=="type":type_el(active,ef,a["id"],a["text"])
            elif act=="clear_and_type":type_el(active,ef,a["id"],a["text"],clear=True)
            elif act=="press_key":active.keyboard.press(a.get("key","Enter"));active.wait_for_timeout(1500)
            elif act=="scroll":active.mouse.wheel(0,500 if a.get("direction","down")=="down" else -500);active.wait_for_timeout(800)
            elif act=="wait":active.wait_for_timeout(a.get("ms",2000))
            elif act=="goto":active.goto(a["url"],wait_until="domcontentloaded");active.wait_for_timeout(3000)
            elif act=="get_text":
                tx=active.evaluate("()=>document.body.innerText");msgs.append({"role":"user","content":"Page text:\n"+tx[:4000]})
        except Exception as e:
            msgs.append({"role":"user","content":"WARN action failed: "+str(e)})
    # Write final state for the orchestrator to read
    try:
        with open(__STATE__,"w") as f:
            json.dump({"url":active.url,"done":done_msg,"text":active.evaluate("()=>document.body.innerText")[:600]},f,ensure_ascii=False)
    except Exception:pass
    # KEEP BROWSER OPEN: sleep indefinitely
    while True:
        time.sleep(3600)
'''


def main(query: str) -> dict:
    state_file = os.path.join(PROJECT_ROOT, "_browser_task_state.json")
    try:
        if os.path.exists(state_file):
            os.remove(state_file)
    except Exception:
        pass
    # Build keeper script with task + state path injected
    code = KEEPER_TEMPLATE.replace("__TASK__", json.dumps(query)).replace("__STATE__", json.dumps(state_file))
    with open(KEEPER, "w") as f:
        f.write(code)
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    # Spawn detached keeper process (survives after this subagent returns)
    cmd = f"cd {PROJECT_ROOT} && DISPLAY=:1 nohup python '{KEEPER}' > {PROJECT_ROOT}/_keeper.log 2>&1 & echo STARTED_PID=$!"
    out = execute_shell_command(cmd)
    # Wait for automation to finish (poll state file)
    import time
    waited = 0
    while waited < 150:
        time.sleep(5)
        waited += 5
        if os.path.exists(state_file):
            break
    final_state = {}
    try:
        if os.path.exists(state_file):
            final_state = json.load(open(state_file))
    except Exception as e:
        final_state = {"error": str(e)}
    log_tail = ""
    try:
        log_tail = execute_shell_command(f"tail -n 40 {PROJECT_ROOT}/_keeper.log 2>&1")
    except Exception:
        pass
    summary = call_llm(
        system="Summarize the browser automation: what was done, final URL/page, whether the target song is shown/playing, and whether the browser is kept open. Be concrete.",
        messages=[{"role": "user", "content": f"Task: {query}\n\nSpawned keeper: {out}\nWaited ~{waited}s.\nFinal state: {json.dumps(final_state, ensure_ascii=False)}\n\nKeeper log tail:\n{log_tail}\n\nWrite a SUMMARY (100-1500 words)."}],
        max_tokens=2000,
    )
    return {"answer": f"Keeper process started ({out.strip()}). Final state: {json.dumps(final_state, ensure_ascii=False)[:1500]}", "summary": summary}
