import json
import os
import re
import numpy as np
from llm import call_llm
from tools import execute_shell_command


def _sh(cmd):
    try:
        return execute_shell_command(cmd)
    except Exception as e:
        return f"ERROR: {e}"


def ensure_deps(evidence):
    out = _sh("pip install -q edge-tts mutagen 2>&1 | tail -3")
    evidence.append("pip install edge-tts mutagen: " + out[:300])
    has = _sh("python -c 'import edge_tts; print(\"OK\")' 2>&1 | tail -1").strip()
    evidence.append("edge_tts import: " + has)
    return ('OK' in has)


def build_plan(query):
    plan = call_llm(
        system="You are an expert at designing focus/relaxation/ambient audio experiences. Parse the user request and return strict JSON. All values must be driven ONLY by the user request.",
        messages=[{"role": "user", "content": (
            f"User request:\n{query}\n\n"
            "Return STRICT JSON with keys:\n"
            "  output_filename: str (mp3 filename; if none, 'ambient_audio.mp3')\n"
            "  target_minutes: number (honor stated range, use midpoint; default 18)\n"
            "  voice_gender: 'male'|'female'|'any'\n"
            "  prompt_placement: describe WHEN spoken prompts occur e.g. 'beginning and midpoint'\n"
            "  prompts: LIST of {at_seconds: number, text: EXACT brief calm spoken prompt 1-3 sentences}. Create exactly the number implied (beginning+midpoint => 2 prompts, one near start, one near middle).\n"
            "  ambient_layers: LIST from [rain,waves,wind,birds,fire,none] matching user-mentioned sounds.\n"
            "  background_music: boolean\n"
            "  music_mood: short mood description\n"
            "  ambient_volume: float 0-1 (low ~0.15-0.3)\n"
            "  music_volume: float 0-1 (low ~0.08-0.18)\n"
            "  voice_volume: float 0-1 (~0.9)\n"
            "  rhythm_hz: float steady rhythm freq (e.g. 0.5) if user wants steady rhythm else 0\n"
            "Return ONLY JSON."
        )}],
        max_tokens=2000,
    )
    m = re.search(r"\{.*\}", plan, re.DOTALL)
    if not m:
        raise ValueError("No JSON plan: " + plan[:300])
    return json.loads(m.group(0))


def pick_voice(gender, evidence):
    male_voices = ["en-US-GuyNeural", "en-US-ChristopherNeural", "en-US-EricNeural", "en-GB-RyanNeural"]
    female_voices = ["en-US-JennyNeural", "en-US-AriaNeural", "en-GB-SoniaNeural"]
    if gender == 'male':
        cands = male_voices
    elif gender == 'female':
        cands = female_voices
    else:
        cands = ["en-US-GuyNeural", "en-US-JennyNeural"]
    for v in cands:
        _sh(f"edge-tts --voice {v} --text 'test' --write-media __vtest.mp3 2>&1 | tail -2")
        if os.path.exists('__vtest.mp3') and os.path.getsize('__vtest.mp3') > 1000:
            evidence.append(f"voice OK: {v}")
            return v
        evidence.append(f"voice fail: {v}")
    return cands[0]


def synth_prompt(voice, text, idx, evidence):
    fn = f"prompt_{idx:02d}.mp3"
    cmd = f"edge-tts --voice {voice} --rate=-15% --text \"{text}\" --write-media {fn} 2>&1 | tail -2"
    out = _sh(cmd)
    ok = os.path.exists(fn) and os.path.getsize(fn) > 1000
    evidence.append(f"prompt {idx} ({len(text)} chars) ok={ok}: {out[:120]}")
    return fn if ok else None


def decode_mp3(path, target_sr=44100):
    import av
    cont = av.open(path)
    stream = cont.streams.audio[0]
    sr = stream.rate
    frames = []
    for frame in cont.decode(stream):
        arr = frame.to_ndarray()
        if arr.ndim > 1:
            arr = arr.mean(axis=0)
        frames.append(arr.astype('float32'))
    cont.close()
    if not frames:
        return np.zeros(0, dtype='float32')
    sig = np.concatenate(frames)
    if sr != target_sr and len(sig) > 0:
        n_out = int(len(sig) * target_sr / sr)
        idx = np.linspace(0, len(sig) - 1, n_out)
        sig = np.interp(idx, np.arange(len(sig)), sig).astype('float32')
    return sig


def make_ambient_layer(kind, n, sr, rng):
    t = np.arange(n) / sr
    if kind == 'rain':
        base = rng.standard_normal(n)
        k = 1500
        sm = np.convolve(base, np.ones(k)/k, mode='same')
        sig = base - sm
        sig *= (0.7 + 0.3*np.sin(2*np.pi*t/9.0))
    elif kind == 'waves':
        base = rng.standard_normal(n)
        sm = np.convolve(base, np.ones(4000)/4000, mode='same')
        sig = sm * (0.5 + 0.5*np.sin(2*np.pi*t/11.0))
    elif kind == 'wind':
        base = rng.standard_normal(n)
        sm = np.convolve(base, np.ones(8000)/8000, mode='same')
        sig = sm * (0.6 + 0.4*np.sin(2*np.pi*t/17.0))
    elif kind == 'birds':
        sig = np.zeros(n)
        for _ in range(max(3, n//(sr*8))):
            pos = rng.integers(0, max(1, n-sr))
            ln = int(sr*0.15)
            tt = np.arange(ln)/sr
            chirp = np.sin(2*np.pi*(2000 + 1500*tt/0.15)*tt) * np.hanning(ln)
            sig[pos:pos+ln] += chirp
    elif kind == 'fire':
        base = rng.standard_normal(n)
        sm = np.convolve(base, np.ones(500)/500, mode='same')
        sig = (base - sm) * (0.5 + 0.5*rng.random(n))
    else:
        return np.zeros(n)
    mx = np.max(np.abs(sig)) + 1e-9
    return sig / mx


def make_music(n, sr, mood):
    base = 110.0
    chords = [[1, 1.5, 2.0], [1, 1.25, 1.5], [1, 1.333, 1.667], [1, 1.5, 1.8]]
    seg_len = int(sr * 8.0)
    out = np.zeros(n)
    idx = 0
    ci = 0
    while idx < n:
        ln = min(seg_len, n - idx)
        tt = np.arange(ln) / sr
        chord = chords[ci % len(chords)]
        seg = np.zeros(ln)
        for h in chord:
            seg += np.sin(2*np.pi*base*h*tt) + 0.3*np.sin(2*np.pi*base*h*2*tt)
        env = np.ones(ln)
        fade = int(sr*1.5)
        if ln > 2*fade:
            env[:fade] = np.linspace(0, 1, fade)
            env[-fade:] = np.linspace(1, 0, fade)
        out[idx:idx+ln] += seg * env
        idx += ln
        ci += 1
    mx = np.max(np.abs(out)) + 1e-9
    return out / mx


def main(query: str) -> dict:
    evidence = []
    if not ensure_deps(evidence):
        evidence.append("edge-tts not available")
    try:
        plan = build_plan(query)
    except Exception as e:
        return {"answer": "FAILED to build plan", "summary": str(e)}
    evidence.append("PLAN: " + json.dumps({k: plan.get(k) for k in ['output_filename','target_minutes','voice_gender','prompt_placement','ambient_layers','background_music','rhythm_hz']}))
    out_name = plan.get('output_filename') or 'ambient_audio.mp3'
    if not out_name.lower().endswith('.mp3'):
        out_name += '.mp3'
    try:
        target_min = float(plan.get('target_minutes', 18))
    except Exception:
        target_min = 18.0
    sr = 44100
    total = int(sr * target_min * 60)
    voice = pick_voice(plan.get('voice_gender', 'male'), evidence)
    prompts = plan.get('prompts', []) or []
    placed = []
    for i, p in enumerate(prompts):
        txt = str(p.get('text', '')).strip()
        if not txt:
            continue
        fn = synth_prompt(voice, txt, i, evidence)
        if fn:
            placed.append((float(p.get('at_seconds', 0)), fn))
    evidence.append(f"prompts synthesized: {len(placed)}/{len(prompts)} voice={voice}")
    rng = np.random.default_rng(7)
    amb_cfg = plan.get('ambient_layers', ['rain'])
    if not amb_cfg:
        amb_cfg = ['rain']
    ambient = np.zeros(total)
    for kind in amb_cfg:
        if kind and kind != 'none':
            ambient += make_ambient_layer(kind, total, sr, rng)
    if ambient.any():
        ambient = ambient / (np.max(np.abs(ambient)) + 1e-9)
    rhythm_hz = float(plan.get('rhythm_hz', 0) or 0)
    if rhythm_hz > 0 and ambient.any():
        t = np.arange(total)/sr
        ambient *= (0.85 + 0.15*np.sin(2*np.pi*rhythm_hz*t))
    amb_vol = float(plan.get('ambient_volume', 0.22) or 0.22)
    mix = ambient * amb_vol
    if plan.get('background_music'):
        music = make_music(total, sr, plan.get('music_mood', 'calm'))
        m_vol = float(plan.get('music_volume', 0.12) or 0.12)
        mix = mix + music * m_vol
        evidence.append("added music layer vol=" + str(m_vol))
    voice_vol = float(plan.get('voice_volume', 0.9) or 0.9)
    for at_s, fn in placed:
        vsig = decode_mp3(fn, sr)
        if len(vsig) == 0:
            continue
        pk = np.max(np.abs(vsig)) + 1e-9
        vsig = vsig / pk * voice_vol
        start = int(at_s * sr)
        if start < 0:
            start = 0
        if start >= total:
            start = max(0, total - len(vsig))
        end = min(total, start + len(vsig))
        mix[start:end] += vsig[:end-start]
        evidence.append(f"voice prompt placed at {at_s}s -> [{start},{end})")
    peak = np.max(np.abs(mix)) + 1e-9
    if peak > 1.0:
        mix = mix / peak * 0.97
    fade = int(sr*3)
    if total > 2*fade:
        mix[:fade] *= np.linspace(0, 1, fade)
        mix[-fade:] *= np.linspace(1, 0, fade)
    try:
        import av
        pcm = np.int16(np.clip(mix, -1, 1) * 32767)
        container = av.open(out_name, mode='w', format='mp3')
        st = container.add_stream('mp3', rate=sr)
        frame = av.AudioFrame.from_ndarray(pcm.reshape(1, -1), format='s16', layout='mono')
        frame.sample_rate = sr
        for packet in st.encode(frame):
            container.mux(packet)
        for packet in st.encode(None):
            container.mux(packet)
        container.close()
        ok = os.path.exists(out_name) and os.path.getsize(out_name) > 50000
        evidence.append(f"PyAV export {out_name} size={os.path.getsize(out_name) if os.path.exists(out_name) else 0} ok={ok}")
    except Exception as e:
        return {"answer": "FAILED export", "summary": "\n".join(evidence) + "\n" + repr(e)}
    dur = 0.0
    try:
        from mutagen.mp3 import MP3
        from mutagen.id3 import ID3, TIT2
        audio = MP3(out_name)
        dur = audio.info.length
        if audio.tags is None:
            audio.add_tags()
        audio.tags.add(TIT2(encoding=3, text='Focus / Ambient Session'))
        audio.save()
    except Exception as e:
        evidence.append("tag err: " + str(e))
    size = os.path.getsize(out_name) if os.path.exists(out_name) else 0
    evidence.append(f"FINAL {out_name} size={size} duration={dur:.1f}s voice={voice}")
    summary = call_llm(
        system="You are a technical writer summarizing an audio generation session.",
        messages=[{"role": "user", "content": f"Task: {query}\n\nPlan: {json.dumps(plan)}\n\nEvidence:\n" + "\n".join(evidence[-30:]) + f"\n\nFinal: {out_name} size={size} duration={dur:.1f}s voice={voice} prompts={len(placed)}\n\nWrite SUMMARY (100-2000 words): voice used and gender, prompts and placement, ambient layers, background music, mixing, duration verification."}],
        max_tokens=2000,
    )
    answer = (f"Generated '{out_name}' ({size} bytes, {dur:.1f}s). Voice={voice} (gender={plan.get('voice_gender')}), ambient={plan.get('ambient_layers')}, music={plan.get('background_music')}, prompts={len(placed)} at {[p[0] for p in placed]}s")
    return {"answer": answer, "summary": summary}
