import json
import os
import re
from llm import call_llm
from tools import execute_shell_command


def _sh(cmd):
    try:
        return execute_shell_command(cmd)
    except Exception as e:
        return f"ERROR: {e}"


# ---------- Plan ----------
def build_plan(query):
    plan = call_llm(
        system="You are an expert ambient/guided-audio producer. Parse the request and return a production plan as STRICT JSON.",
        messages=[{"role": "user", "content": (
            f"User request:\n{query}\n\n"
            "Return STRICT JSON with keys:\n"
            "  output_filename (str, e.g. 'focus_music.mp3'),\n"
            "  target_minutes (number, e.g. 18),\n"
            "  ambient (one of rain/waves/wind),\n"
            "  include_rhythm (bool - add a subtle steady musical pulse/beat),\n"
            "  rhythm_bpm (int, ~60 for calm steady rhythm),\n"
            "  ambient_volume (float 0.0-0.2, e.g. 0.09),\n"
            "  sections: LIST of objects with keys 'title', 'text', 'position_ratio'. "
            "'text' is the EXACT spoken narration (calm, second-person). 'position_ratio' is a float 0.0-1.0 giving WHERE on the total timeline this voice plays "
            "(intro ~0.01, midpoint ~0.5, etc). Keep each section brief if the request asks for brief prompts. "
            "Only include the sections the request explicitly asks for (e.g. if only beginning+midpoint prompts, include just 2 sections).\n"
            "Return ONLY JSON."
        )}],
        max_tokens=4000,
    )
    m = re.search(r"\{.*\}", plan, re.DOTALL)
    if not m:
        raise ValueError("No JSON plan: " + plan[:300])
    return json.loads(m.group(0))


# ---------- TTS ----------
def synthesize(plan, evidence):
    out = []
    for i, sec in enumerate(plan.get("sections", [])):
        text = str(sec.get("text", "")).strip()
        if not text:
            continue
        ratio = float(sec.get("position_ratio", i / max(1, len(plan.get("sections", []) ))))
        safe = json.dumps(text)
        seg = f"seg_{i:02d}.mp3"
        py = ("from gtts import gTTS;" f"t={safe};" f"gTTS(text=t, lang='en', slow=True).save('{seg}')")
        r = _sh(f"python -c {json.dumps(py)}")
        evidence.append(f"TTS {i} ({len(text)}c) -> {seg} ratio={ratio}: {r[:120]}")
        if os.path.exists(seg) and os.path.getsize(seg) > 1000:
            out.append((seg, ratio))
    return out


# ---------- Audio synthesis helpers (numpy) ----------
NP_HELPERS = r'''
import numpy as np
SR=44100

def gen_ambient(kind, seconds, sr=SR, vol=0.09, rng_seed=7):
    n=int(sr*seconds); t=np.arange(n)/sr
    rng=np.random.default_rng(rng_seed)
    base=rng.standard_normal(n)
    if kind=='waves':
        k=4000; sm=np.convolve(base,np.ones(k)/k,mode='same')
        sig=sm*(0.5+0.5*np.sin(2*np.pi*t/11.0))
    elif kind=='wind':
        k=8000; sm=np.convolve(base,np.ones(k)/k,mode='same')
        sig=sm*(0.6+0.4*np.sin(2*np.pi*t/17.0))
    else: # rain
        k=2000; sm=np.convolve(base,np.ones(k)/k,mode='same')
        sig=base-sm
        sig*=(0.75+0.25*np.sin(2*np.pi*t/9.0))
    sig=sig/(np.max(np.abs(sig))+1e-9)*vol
    fade=int(sr*2)
    if n>2*fade:
        sig[:fade]*=np.linspace(0,1,fade); sig[-fade:]*=np.linspace(1,0,fade)
    return sig.astype('float32')

def gen_rhythm(seconds, bpm=60, sr=SR, vol=0.04):
    # subtle soft sine-bell pulse on the beat + faint low drone, very low volume
    n=int(sr*seconds); t=np.arange(n)/sr
    sig=np.zeros(n,dtype='float64')
    beat=60.0/bpm
    nb=int(seconds/beat)+1
    for b in range(nb):
        start=int(b*beat*sr)
        if start>=n: break
        # soft bell: a short decaying sine at ~220Hz
        length=int(0.6*sr)
        end=min(n,start+length)
        tt=np.arange(end-start)/sr
        env=np.exp(-tt*6.0)
        bell=np.sin(2*np.pi*220*tt)*env
        sig[start:end]+=bell
    # gentle pad drone
    drone=0.3*np.sin(2*np.pi*110*t)+0.2*np.sin(2*np.pi*165*t)
    sig=sig+drone*0.15
    sig=sig/(np.max(np.abs(sig))+1e-9)*vol
    fade=int(sr*2)
    if n>2*fade:
        sig[:fade]*=np.linspace(0,1,fade); sig[-fade:]*=np.linspace(1,0,fade)
    return sig.astype('float32')
'''


def main(query: str) -> dict:
    evidence = []
    _sh("pip install -q gTTS mutagen numpy av 2>&1 | tail -1")

    try:
        plan = build_plan(query)
    except Exception as e:
        return {"answer": "FAILED to build plan", "summary": str(e)}
    evidence.append("PLAN: " + json.dumps({k: plan.get(k) for k in ['output_filename','target_minutes','ambient','include_rhythm','rhythm_bpm']}) + " sections=" + str([(s.get('title'), s.get('position_ratio')) for s in plan.get('sections', [])]))

    out_name = plan.get("output_filename") or "focus_music.mp3"
    if not out_name.lower().endswith('.mp3'):
        out_name += '.mp3'
    try:
        target_min = float(plan.get("target_minutes", 18) or 18)
    except Exception:
        target_min = 18.0

    segs = synthesize(plan, evidence)
    if not segs:
        return {"answer": "FAILED: no segments", "summary": "\n".join(evidence)}

    # ---- Build full-length timeline with numpy + PyAV decode of voice ----
    import numpy as np
    import av
    exec(NP_HELPERS, globals())  # define gen_ambient, gen_rhythm as module globals
    SR = 44100
    total_samples = int(SR * target_min * 60)

    def decode_mp3(path):
        cont = av.open(path); stream = cont.streams.audio[0]; sr = stream.rate
        frames = []
        for frame in cont.decode(stream):
            a = frame.to_ndarray()
            if a.ndim > 1: a = a.mean(axis=0)
            frames.append(a.astype('float32'))
        cont.close()
        sig = np.concatenate(frames) if frames else np.zeros(0, dtype='float32')
        if sr != SR and len(sig) > 0:
            idx = np.linspace(0, len(sig)-1, int(len(sig)*SR/sr))
            sig = np.interp(idx, np.arange(len(sig)), sig).astype('float32')
        return sig

    # ambient + rhythm bed
    ambient = gen_ambient(plan.get("ambient", "rain"), target_min*60, SR, vol=float(plan.get("ambient_volume", 0.09) or 0.09))
    if len(ambient) < total_samples:
        ambient = np.tile(ambient, total_samples//len(ambient)+1)
    ambient = ambient[:total_samples]
    bed = ambient.copy()
    if plan.get("include_rhythm", True):
        rhythm = gen_rhythm(target_min*60, int(plan.get("rhythm_bpm", 60) or 60), SR, vol=0.035)
        if len(rhythm) < total_samples:
            rhythm = np.tile(rhythm, total_samples//len(rhythm)+1)
        bed = bed + rhythm[:total_samples]

    # place voice at positional ratios
    voice_track = np.zeros(total_samples, dtype='float32')
    for seg, ratio in segs:
        sig = decode_mp3(seg)
        if len(sig) == 0:
            continue
        sig = sig / (np.max(np.abs(sig))+1e-9) * 0.85
        pos = int(min(max(ratio, 0.0), 1.0) * total_samples)
        # avoid clipping past end
        end = min(total_samples, pos + len(sig))
        voice_track[pos:end] += sig[:end-pos]
        evidence.append(f"placed {seg} at sample {pos} ({pos/SR:.1f}s, ratio={ratio})")

    mix = voice_track + bed
    # normalize
    mix = mix / (np.max(np.abs(mix))+1e-9) * 0.95
    fade = int(SR*3)
    mix[:fade] *= np.linspace(0, 1, fade)
    mix[-fade:] *= np.linspace(1, 0, fade)

    # encode via PyAV
    try:
        container = av.open(out_name, mode='w', format='mp3')
        stream = container.add_stream('mp3', rate=SR)
        stream.bit_rate = 128000
        pcm = np.int16(np.clip(mix, -1, 1) * 32767)
        frame = av.AudioFrame.from_ndarray(pcm.reshape(1, -1), format='s16', layout='mono')
        frame.sample_rate = SR
        for packet in stream.encode(frame):
            container.mux(packet)
        for packet in stream.encode(None):
            container.mux(packet)
        container.close()
        evidence.append("PyAV encode done")
    except Exception as e:
        evidence.append("PyAV encode error: " + repr(e))

    ok = os.path.exists(out_name) and os.path.getsize(out_name) > 50000
    size = os.path.getsize(out_name) if os.path.exists(out_name) else 0
    dur = f"duration={total_samples/SR:.1f}s"

    # tag
    try:
        from mutagen.id3 import ID3, TIT2
        from mutagen.mp3 import MP3
        a = MP3(out_name)
        if a.tags is None:
            a.add_tags()
        a.tags.add(TIT2(encoding=3, text="Focus Music"))
        a.save()
        dur = f"duration={MP3(out_name).info.length:.1f}s"
    except Exception as e:
        evidence.append("tag err: " + str(e))

    evidence.append(f"FINAL {out_name} size={size} ok={ok} {dur}")

    summary = call_llm(
        system="You are an audio-production summarizer.",
        messages=[{"role": "user", "content": f"Task: {query}\n\nEvidence:\n" + "\n".join(evidence[-20:]) + f"\n\nWrite a SUMMARY of what was produced: sections and their positional placement, ambient type, rhythm layer, mixing, and verification (size/duration)."}],
        max_tokens=1200,
    )
    answer = f"Generated '{out_name}' size={size} ok={ok} {dur}. Sections placed: {[(s.get('title'), s.get('position_ratio')) for s in plan.get('sections',[])]}"
    return {"answer": answer, "summary": summary}
