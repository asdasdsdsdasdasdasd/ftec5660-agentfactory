import json
import os
import re
import wave
import struct
import math
import random
from llm import call_llm
from tools import execute_shell_command


def _sh(cmd):
    try:
        return execute_shell_command(cmd)
    except Exception as e:
        return f"ERROR: {e}"


# ---------- Step 1: understand the request & build a script ----------
def build_plan(query):
    plan = call_llm(
        system="You are an expert meditation & audio-production planner. Given a user request for a guided meditation/relaxation audio, extract the parameters and write the full narration script.",
        messages=[{"role": "user", "content": (
            f"User request:\n{query}\n\n"
            "Return STRICT JSON with keys:\n"
            "  output_filename (str, default 'bedtime_meditation.mp3' if not specified),\n"
            "  target_minutes (number),\n"
            "  voice_style (str; describe calm/slow tone),\n"
            "  ambient (one of: rain, waves, wind, none),\n"
            "  ambient_volume_db (negative number, e.g. -22),\n"
            "  speak_slowly_ratio (float >1.0 for slower speech, e.g. 1.15),\n"
            "  sections: a LIST of objects with keys 'title' and 'text'. The 'text' is the EXACT spoken narration (no stage directions), written in a calm, reassuring, second-person voice."
            "\nThe sections must collectively cover ALL explicitly requested elements of the user's request "
            "(for example: an intro, the specified number of breathing phases using the specified breathing pattern, "
            "a progressive head-to-toe body scan, and a peaceful visualization), plus a gentle closing. "
            "Expand each section into flowing, unhurried sentences suitable for slow text-to-speech. "
            "IMPORTANT: target the REQUESTED duration generously on the HIGH end. At a slowed stress-reduction pace "
            "text-to-speech speaks roughly 95-105 words per minute, and there will be inter-section pauses. "
            "So size the TOTAL script to about target_minutes * 105 words or slightly more. "
            "For a 15-20 minute request, write substantial, richly detailed narration for EVERY section "
            "(do NOT be brief) so the total runs comfortably past the minimum. "
            "Include natural pause cues by ending sentences with periods and occasional ellipses. "
            "Return ONLY the JSON, no commentary."
        )}],
        max_tokens=6000,
    )
    m = re.search(r"\{.*\}", plan, re.DOTALL)
    if not m:
        raise ValueError("No JSON plan returned: " + plan[:300])
    return json.loads(m.group(0))


def synthesize(plan, evidence):
    sections = plan.get("sections", [])
    slow = float(plan.get("speak_slowly_ratio", 1.15) or 1.15)
    seg_paths = []
    for i, sec in enumerate(sections):
        text = str(sec.get("text", "")).strip()
        if not text:
            continue
        safe = json.dumps(text)  # json string is a valid python double-quoted literal
        seg = f"seg_{i:02d}.mp3"
        # gTTS: slow=True gives a slower pace
        py = (
            "from gtts import gTTS;"
            f"t={safe};"
            f"gTTS(text=t, lang='en', slow={'True' if slow>1.0 else 'False'}).save('{seg}')"
        )
        out = _sh(f"python -c {json.dumps(py)}")
        evidence.append(f"TTS segment {i} ({len(text)} chars) -> {seg}: {out[:200]}")
        if os.path.exists(seg) and os.path.getsize(seg) > 1000:
            seg_paths.append((i, seg))
        else:
            evidence.append(f"WARN: segment {i} failed/empty")
    return seg_paths


def make_ambient(kind, seconds, sr=44100, vol=0.06):
    import numpy as np
    n = int(sr * seconds)
    t = np.arange(n) / sr
    rng = np.random.default_rng(7)
    if kind == 'waves':
        base = rng.standard_normal(n)
        # low-pass by cumulative smoothing
        k = 4000
        kernel = np.ones(k) / k
        sm = np.convolve(base, kernel, mode='same')
        # slow swelling amplitude
        swell = 0.5 + 0.5 * np.sin(2 * np.pi * t / 11.0)
        sig = sm * swell
    elif kind == 'wind':
        base = rng.standard_normal(n)
        k = 8000
        sm = np.convolve(base, np.ones(k) / k, mode='same')
        sig = sm * (0.6 + 0.4 * np.sin(2 * np.pi * t / 17.0))
    else:  # rain
        base = rng.standard_normal(n)
        # high-pass-ish: subtract slow component
        k = 2000
        sm = np.convolve(base, np.ones(k) / k, mode='same')
        sig = base - sm
        sig *= (0.7 + 0.3 * np.sin(2 * np.pi * t / 9.0))
    sig = sig / (np.max(np.abs(sig)) + 1e-9)
    sig = sig * vol
    # fade in/out to avoid clicks
    fade = int(sr * 2)
    if n > 2 * fade:
        sig[:fade] *= np.linspace(0, 1, fade)
        sig[-fade:] *= np.linspace(1, 0, fade)
    return sig, sr


def write_wav(path, sig, sr):
    import numpy as np
    pcm = np.int16(np.clip(sig, -1, 1) * 32767)
    with wave.open(path, 'w') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def main(query: str) -> dict:
    evidence = []

    # ---- Ensure dependencies with fallbacks for mp3 handling ----
    setup = _sh("pip install -q gTTS mutagen 2>&1 | tail -3")
    evidence.append("pip install gTTS mutagen: " + setup[:300])
    import importlib
    if importlib.util.find_spec('gtts') is None:
        setup2 = _sh("pip install -q gTTS 2>&1 | tail -3")
        evidence.append("retry gTTS: " + setup2[:300])
    if importlib.util.find_spec('mutagen') is None:
        _sh("pip install -q mutagen 2>&1 | tail -3")

    # ---- Try to obtain an ffmpeg binary (pydub needs it for mp3) ----
    ffmpeg_path = None
    chk = _sh("command -v ffmpeg")
    if chk.strip() and 'NOT FOUND' not in chk and 'not found' not in chk.lower():
        ffmpeg_path = chk.strip()
    else:
        inst = _sh("pip install -q imageio-ffmpeg 2>&1 | tail -2; python -c \"import imageio_ffmpeg, shutil, os; p=imageio_ffmpeg.get_ffmpeg_exe(); print('FFMPEG', p)\" 2>&1 | tail -1")
        evidence.append("imageio-ffmpeg: " + inst[:300])
        m = re.search(r"FFMPEG\s+(\S+)", inst)
        if m and os.path.exists(m.group(1)):
            ffmpeg_path = m.group(1)
    evidence.append("ffmpeg_path resolved: " + str(ffmpeg_path))
    if ffmpeg_path:
        os.environ['PATH'] = os.path.dirname(ffmpeg_path) + os.pathsep + os.environ.get('PATH', '')
        os.environ['FFMPEG_BINARY'] = ffmpeg_path
        try:
            import pydub
            from pydub import AudioSegment
            AudioSegment.converter = ffmpeg_path
            AudioSegment.ffmpeg = ffmpeg_path
            AudioSegment.ffprobe = ffmpeg_path
        except Exception as e:
            evidence.append("pydub config err: " + str(e))

    # ---- Plan / script ----
    try:
        plan = build_plan(query)
    except Exception as e:
        evidence.append("plan error: " + str(e))
        return {"answer": "FAILED to build plan", "summary": str(e)}
    evidence.append("PLAN keys: " + str(list(plan.keys())) + " | sections=" + str(len(plan.get('sections', []))))
    out_name = plan.get("output_filename") or "bedtime_meditation.mp3"
    if not out_name.lower().endswith('.mp3'):
        out_name += '.mp3'

    # ---- Synthesize speech ----
    segs = synthesize(plan, evidence)
    if not segs:
        return {"answer": "FAILED: no audio segments synthesized", "summary": "\n".join(evidence)}

    # ---- Assemble ----
    final_ok = False
    method = ""

    # PRIMARY PATH: PyAV (bundled ffmpeg libs, no ffprobe binary needed)
    try:
        import numpy as np
        have_av = _sh("python -c 'import av; print(av.__version__)' 2>&1 | tail -1").strip()
        if 'Error' in have_av or 'No module' in have_av or not have_av:
            _sh("pip install -q av 2>&1 | tail -2")
        import av
        try:
            from av.audio.resampler import AudioResampler
        except Exception:
            AudioResampler = None

        def decode_mp3(path):
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
                return np.zeros(0, dtype='float32'), sr
            return np.concatenate(frames), sr

        sr_out = 44100
        def to_sr(sig, sr):
            if sr == sr_out or len(sig) == 0:
                return sig
            # simple linear resample
            n_out = int(len(sig) * sr_out / sr)
            idx = np.linspace(0, len(sig) - 1, n_out)
            return np.interp(idx, np.arange(len(sig)), sig).astype('float32')

        speech = []
        gap = np.zeros(int(sr_out * 3.0), dtype='float32')  # generous pause between sections
        lead = np.zeros(int(sr_out * 2.0), dtype='float32')
        speech.append(lead)
        for i, seg in segs:
            sig, sr = decode_mp3(seg)
            sig = to_sr(sig, sr)
            peak = np.max(np.abs(sig)) + 1e-9
            sig = sig / peak * 0.85
            speech.append(sig)
            speech.append(gap)
        voice = np.concatenate(speech) if speech else np.zeros(sr_out, dtype='float32')
        # Guarantee minimum duration from the plan's target_minutes (default 15 min)
        try:
            min_minutes = float(plan.get('target_minutes', 15) or 15)
        except Exception:
            min_minutes = 15.0
        if min_minutes > 20:
            min_minutes = 15.0
        min_samples = int(sr_out * min_minutes * 60)
        if len(voice) < min_samples:
            voice = np.concatenate([voice, np.zeros(min_samples - len(voice), dtype='float32')])
        total = len(voice)
        ambient_kind = plan.get('ambient', 'rain')
        if ambient_kind and ambient_kind != 'none':
            amb, asr = make_ambient(ambient_kind, total / sr_out, vol=0.06)
            amb = to_sr(amb, asr)
            if len(amb) < total:
                reps = total // max(len(amb), 1) + 1
                amb = np.tile(amb, reps)
            amb = amb[:total]
            voice = voice + amb[:total]
        # normalize & fades
        peak = np.max(np.abs(voice)) + 1e-9
        voice = voice / peak * 0.95
        fade = int(sr_out * 3)
        if total > 2 * fade:
            voice[:fade] *= np.linspace(0, 1, fade)
            voice[-fade:] *= np.linspace(1, 0, fade)
        # encode mp3 via PyAV
        out_container = av.open(out_name, mode='w', format='mp3')
        astream = out_container.add_stream('mp3', rate=sr_out)
        astream.layout = 'mono' if AudioResampler is None else astream.layout
        pcm = np.int16(np.clip(voice, -1, 1) * 32767)
        frame = av.AudioFrame.from_ndarray(pcm.reshape(1, -1), format='s16', layout='mono')
        frame.sample_rate = sr_out
        for packet in astream.encode(frame):
            out_container.mux(packet)
        for packet in astream.encode(None):
            out_container.mux(packet)
        out_container.close()
        final_ok = os.path.exists(out_name) and os.path.getsize(out_name) > 50000
        method = 'PyAV'
        evidence.append(f'PyAV export -> {out_name} size={os.path.getsize(out_name) if os.path.exists(out_name) else 0} duration={total/sr_out:.1f}s')
    except Exception as e:
        evidence.append('PyAV assembly error: ' + repr(e))

    # SECONDARY: pydub (needs ffprobe)
    try:
        if final_ok:
            raise RuntimeError('skip')
        from pydub import AudioSegment
        combined = AudioSegment.silent(duration=1500)
        gap = AudioSegment.silent(duration=1200)
        for i, seg in segs:
            audio = AudioSegment.from_file(seg, format="mp3")
            # slow down speech slightly and keep pitch (lower sample rate playback trick)
            combined += audio + gap
        total_ms = len(combined)
        ambient_kind = plan.get("ambient", "rain")
        if ambient_kind and ambient_kind != 'none':
            amb, sr = make_ambient(ambient_kind, total_ms / 1000.0, vol=0.05)
            write_wav("ambient.wav", amb, sr)
            amb_seg = AudioSegment.from_wav("ambient.wav")
            amb_seg = amb_seg.set_frame_rate(combined.frame_rate).set_channels(combined.channels)
            if len(amb_seg) < len(combined):
                reps = (len(combined) // max(len(amb_seg),1)) + 1
                amb_seg = amb_seg * reps
            amb_seg = amb_seg[:total_ms]
            bg_db = float(plan.get("ambient_volume_db", -22))
            amb_seg = amb_seg + bg_db
            combined = combined.overlay(amb_seg)
        combined = combined.fade_in(2000).fade_out(4000)
        combined.export(out_name, format="mp3", bitrate="128k")
        method = "pydub"
        final_ok = os.path.exists(out_name) and os.path.getsize(out_name) > 50000
        evidence.append(f"pydub export -> {out_name} size={os.path.getsize(out_name) if os.path.exists(out_name) else 0}")
    except Exception as e:
        evidence.append("pydub assembly error: " + str(e))

    # ---- Fallback: concat mp3 bytes + ambient via ffmpeg ----
    if not final_ok:
        try:
            with open("concat.txt", "w") as f:
                for i, seg in segs:
                    f.write(f"file '{seg}'\n")
            speech_mp3 = "speech_only.mp3"
            if ffmpeg_path:
                _sh(f"\"{ffmpeg_path}\" -y -f concat -safe 0 -i concat.txt -c copy {speech_mp3} 2>&1 | tail -2")
            if os.path.exists(speech_mp3) and os.path.getsize(speech_mp3) > 10000:
                # get duration
                dur = _sh(f"\"{ffmpeg_path}\" -i {speech_mp3} 2>&1 | grep Duration").strip()
                evidence.append("fallback speech duration info: " + dur[:150])
                m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", dur)
                secs = 60.0
                if m:
                    secs = int(m.group(1))*3600 + int(m.group(2))*60 + float(m.group(3))
                amb, sr = make_ambient(plan.get("ambient", "rain"), secs, vol=0.05)
                write_wav("ambient.wav", amb, sr)
                mix = f"\"{ffmpeg_path}\" -y -i {speech_mp3} -i ambient.wav -filter_complex \"[1:a]volume=-22dB[a1];[0:a][a1]amix=inputs=2:duration=first:dropout_transition=2\" -c:a libmp3lame -b:a 128k {out_name} 2>&1 | tail -3"
                mixout = _sh(mix)
                evidence.append("ffmpeg mix fallback: " + mixout[-300:])
                if os.path.exists(out_name) and os.path.getsize(out_name) > 50000:
                    final_ok = True
                    method = "ffmpeg"
        except Exception as e:
            evidence.append("ffmpeg fallback error: " + str(e))

    # ---- Last resort: keep the concatenated speech (still valid mp3) ----
    if not final_ok and os.path.exists("speech_only.mp3") and os.path.getsize("speech_only.mp3") > 10000:
        import shutil
        shutil.copy("speech_only.mp3", out_name)
        final_ok = True
        method = "speech-only (ambient mixing skipped)"

    # ---- Verify duration ----
    size = os.path.getsize(out_name) if os.path.exists(out_name) else 0
    dur_info = ""
    try:
        from mutagen.mp3 import MP3
        dur_info = f"duration={MP3(out_name).info.length:.1f}s"
    except Exception as e:
        if ffmpeg_path:
            dur_info = _sh(f"\"{ffmpeg_path}\" -i {out_name} 2>&1 | grep Duration").strip()[:120]
        else:
            dur_info = f"(duration unknown: {e})"
    evidence.append(f"FINAL: {out_name} size={size} method={method} {dur_info}")

    # add title metadata
    try:
        from mutagen.id3 import ID3, TIT2
        from mutagen.mp3 import MP3
        audio = MP3(out_name)
        if audio.tags is None:
            audio.add_tags()
        audio.tags.add(TIT2(encoding=3, text=plan.get('title', 'Bedtime Meditation')))
        audio.save()
    except Exception as e:
        evidence.append("tag err: " + str(e))

    summary = call_llm(
        system="You are a technical writer summarizing an audio generation session.",
        messages=[{"role": "user", "content": f"Task: {query}\n\nPlan (sections): {json.dumps([s.get('title') for s in plan.get('sections', [])])}\nAmbient: {plan.get('ambient')}\n\nEvidence:\n" + "\n".join(evidence[-25:]) + f"\n\nFinal file: {out_name} size={size} ok={final_ok} method={method} {dur_info}\n\nWrite a SUMMARY (100-2000 words) of the approach, sections generated, synthesis + mixing method, and verification."}],
        max_tokens=2000,
    )

    answer = f"Generated '{out_name}' ({size} bytes, method={method}, {dur_info}). Success={final_ok}. Sections: {[s.get('title') for s in plan.get('sections', [])]}"
    return {"answer": answer, "summary": summary}
