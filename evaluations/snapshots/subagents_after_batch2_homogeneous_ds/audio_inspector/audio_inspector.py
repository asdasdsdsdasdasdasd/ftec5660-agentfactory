import os
import json
import re
from llm import call_llm
from tools import execute_shell_command


def _sh(cmd):
    try:
        return execute_shell_command(cmd)
    except Exception as e:
        return f"ERROR: {e}"


def main(query: str) -> dict:
    evidence = []
    parsed = call_llm(
        system="You extract parameters from an audio-inspection request. Return STRICT JSON only.",
        messages=[{"role": "user", "content": (f"Request:\n{query}\n\nReturn JSON with key 'audio_file' (the filename to inspect). If no filename given, use 'focus_music.mp3'. Return ONLY JSON.")}],
        max_tokens=300,
    )
    audio_file = "focus_music.mp3"
    try:
        m = re.search(r"\{.*\}", parsed, re.DOTALL)
        if m:
            audio_file = json.loads(m.group(0)).get("audio_file", audio_file)
    except Exception as e:
        evidence.append(f"parse err: {e}")

    _sh("pip install -q mutagen numpy av 2>&1 | tail -1")
    exists = os.path.exists(audio_file)
    size = os.path.getsize(audio_file) if exists else 0
    evidence.append(f"File exists={exists} size={size}")
    if not exists:
        return {"answer": f"File {audio_file} not found", "summary": "No file to inspect."}

    info = _sh("python -c \"from mutagen.mp3 import MP3; a=MP3('" + audio_file + "'); print('DURATION', round(a.info.length,2)); print('BITRATE', a.info.bitrate); print('SR', a.info.sample_rate); print('CH', a.info.channels)\" 2>&1 | tail -10")
    evidence.append("mutagen info: " + info[:400])

    analysis_py = "import os, sys, numpy as np\nf = sys.argv[1]\ntry:\n    import av\nexcept Exception:\n    os.system('pip install -q av 2>&1 | tail -1')\n    import av\ncont = av.open(f)\nstream = cont.streams.audio[0]\nsr = stream.rate\nframes=[]\nfor frame in cont.decode(stream):\n    arr = frame.to_ndarray()\n    if arr.ndim>1: arr = arr.mean(axis=0)\n    frames.append(arr.astype('float32'))\ncont.close()\nsig = np.concatenate(frames) if frames else np.zeros(1,dtype='float32')\nsig = sig/(np.max(np.abs(sig))+1e-9)\nwin = int(sr)\nn = len(sig)//win\nrms=[]\nfor i in range(n):\n    seg = sig[i*win:(i+1)*win]\n    rms.append(float(np.sqrt(np.mean(seg**2))))\nrms=np.array(rms)\nprint('TOTAL_SEC', round(len(sig)/sr,1))\nprint('MEAN_RMS', round(float(np.mean(rms)),4))\nprint('MAX_RMS', round(float(np.max(rms)),4))\nstep=30\nfor i in range(0, n, step):\n    print('BIN', i, round(float(np.mean(rms[i:i+step])),4))\n"
    with open("_an.py", "w") as fh:
        fh.write(analysis_py)
    out = _sh(f"python _an.py {audio_file} 2>&1 | tail -80")
    evidence.append("ENVELOPE ANALYSIS:\n" + out[:3000])

    total_sec = None
    bins = []
    for line in out.splitlines():
        if line.startswith("TOTAL_SEC"):
            try:
                total_sec = float(line.split()[1])
            except Exception:
                pass
        elif line.startswith("BIN"):
            parts = line.split()
            try:
                bins.append((int(parts[1]), float(parts[3])))
            except Exception:
                pass

    voice_regions = []
    if bins and total_sec:
        vals = [b[1] for b in bins]
        mean_v = sum(vals) / len(vals)
        thresh = mean_v * 1.6
        for start, val in bins:
            if val > thresh:
                voice_regions.append(start)

    summary = call_llm(
        system="You are an audio QA analyst. Write a detailed SUMMARY of what the audio file inspection revealed.",
        messages=[{"role": "user", "content": (f"Task: {query}\n\nAudio file: {audio_file}\nDetected loud (voice-like) 30s-bin start times: {voice_regions}\nTotal duration: {total_sec} sec\n\nEvidence:\n" + "\n".join(evidence[-6:])[:6000] + "\n\nWrite a SUMMARY describing: real file duration, bitrate, where the louder (voice) regions occur relative to the total (near start only vs near midpoint), and whether ambient audio is sustained throughout. Be factual and cite the numbers.")}],
        max_tokens=1500,
    )
    answer = f"File={audio_file} exists={exists} size={size} duration_sec={total_sec} voice_bin_starts={voice_regions}"
    return {"answer": answer, "summary": summary}
