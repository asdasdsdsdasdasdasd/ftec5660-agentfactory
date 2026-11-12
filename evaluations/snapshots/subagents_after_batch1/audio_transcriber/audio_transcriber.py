import json, re, os
from llm import call_llm
from tools import execute_shell_command


def main(query: str) -> dict:
    evidence = []

    # Step 1: LLM parses the query to find the audio file path (and optional language)
    plan_raw = call_llm(
        system="You extract structured info from a request. Return ONLY JSON.",
        messages=[{"role": "user", "content": f"Query: {query}\n\nExtract the absolute path to the audio file to transcribe and an optional language code (else empty). Return JSON: {{\"audio_path\": \"...\", \"language\": \"\"}}"}],
        max_tokens=300,
    )
    audio_path = ""
    language = ""
    try:
        m = re.search(r"\{.*\}", plan_raw, re.DOTALL)
        if m:
            p = json.loads(m.group(0))
            audio_path = (p.get("audio_path") or "").strip()
            language = (p.get("language") or "").strip()
    except Exception as e:
        evidence.append(f"parse error: {e}; raw={plan_raw}")
    if not audio_path:
        audio_path = query.strip().split()[0]

    evidence.append(f"Target audio: {audio_path}")
    exists = execute_shell_command(f"ls -la '{audio_path}' 2>&1")
    evidence.append(f"ls: {exists}")
    if "No such file" in exists or "cannot access" in exists:
        return {"answer": "Audio file not found: " + audio_path, "summary": "ls result: " + exists}

    # Step 2: Ensure ffmpeg exists (use imageio-ffmpeg static binary if system ffmpeg missing)
    ffmpeg_bin = ""
    sys_ff = execute_shell_command("command -v ffmpeg 2>&1")
    if sys_ff and "not found" not in sys_ff and sys_ff.strip():
        ffmpeg_bin = sys_ff.strip().splitlines()[-1].strip()
    else:
        evidence.append("System ffmpeg missing; installing imageio-ffmpeg for a bundled binary.")
        inst = execute_shell_command("pip install -q imageio-ffmpeg 2>&1 | tail -3")
        evidence.append(f"pip imageio-ffmpeg: {inst}")
        fb = execute_shell_command("python -c \"import imageio_ffmpeg,shutil;print(imageio_ffmpeg.get_ffmpeg_exe())\" 2>&1")
        evidence.append(f"bundled ffmpeg: {fb}")
        cand = fb.strip().splitlines()[-1].strip()
        if cand and os.path.exists(cand):
            ffmpeg_bin = cand

    # Step 3: Convert input to 16k mono wav if possible; otherwise pass original path
    wav_path = "/tmp/_transcribe_input.wav"
    converted = False
    if ffmpeg_bin:
        conv = execute_shell_command(f"'{ffmpeg_bin}' -y -i '{audio_path}' -ar 16000 -ac 1 '{wav_path}' 2>&1 | tail -3")
        evidence.append(f"ffmpeg convert: {conv}")
        converted = os.path.exists(wav_path)
    if not converted:
        wav_path = audio_path
        evidence.append("WAV conversion unavailable; passing original audio path directly to transcriber.")

    transcribe = ""
    # Step 4a: Try faster-whisper (efficient)
    fw_check = execute_shell_command("python -c \"import faster_whisper; print('OK')\" 2>&1 | tail -1")
    if "OK" in fw_check:
        evidence.append("faster_whisper present")
    else:
        evidence.append("Installing faster-whisper...")
        inst = execute_shell_command("pip install -q faster-whisper 2>&1 | tail -3")
        evidence.append(f"pip faster-whisper: {inst}")
        fw_check = execute_shell_command("python -c \"import faster_whisper; print('OK')\" 2>&1 | tail -1")
        evidence.append(f"faster_whisper post-install: {fw_check}")

    if "OK" in fw_check:
        lang_arg = f", language='{language}'" if language else ""
        code = (
            "from faster_whisper import WhisperModel;\n"
            "m = WhisperModel('small', device='cpu', compute_type='int8');\n"
            f"segs, info = m.transcribe(r'{wav_path}'{lang_arg});\n"
            "text = ' '.join(s.text.strip() for s in segs);\n"
            "print('LANG:', info.language);\n"
            "print('TEXT_START');\n"
            "print(text)"
        )
        open('/tmp/_do_transcribe.py', 'w').write(code)
        transcribe = execute_shell_command("python /tmp/_do_transcribe.py 2>&1")
        evidence.append(f"faster-whisper output: {transcribe[:3000]}")

    transcript = ""
    if "TEXT_START" in transcribe:
        transcript = transcribe.split("TEXT_START", 1)[1].strip()

    # Step 4b: fallback to openai-whisper if faster-whisper failed
    if not transcript:
        evidence.append("faster-whisper failed or empty; trying openai-whisper.")
        inst = execute_shell_command("pip install -q openai-whisper 2>&1 | tail -3")
        evidence.append(f"pip openai-whisper: {inst}")
        code2 = (
            "import whisper;\n"
            "m = whisper.load_model('small');\n"
            f"r = m.transcribe(r'{wav_path}'" + (f", language='{language}'" if language else "") + ");\n"
            "print('TEXT_START');\n"
            "print(r.get('text',''))"
        )
        open('/tmp/_do_transcribe2.py', 'w').write(code2)
        t2 = execute_shell_command("python /tmp/_do_transcribe2.py 2>&1")
        evidence.append(f"openai-whisper output: {t2[:3000]}")
        if "TEXT_START" in t2:
            transcript = t2.split("TEXT_START", 1)[1].strip()

    if not transcript:
        summary = call_llm(
            system="You are a diagnostics reporter. The transcription attempts all failed. Summarize what was tried and the errors, and suggest fixes.",
            messages=[{"role": "user", "content": "Evidence:\n" + "\n".join(evidence)}],
            max_tokens=1500,
        )
        return {"answer": "TRANSCRIPTION_FAILED", "summary": summary}

    summary = call_llm(
        system="You are a research summarizer. Write a detailed SUMMARY of the transcription process and the transcribed content.",
        messages=[{"role": "user", "content": f"Query: {query}\n\nTranscribed text:\n{transcript}\n\nEvidence of process:\n" + "\n".join(evidence)[:4000] + "\n\nWrite a SUMMARY (100-2000 words) describing: what audio was transcribed, tools used, and the full transcribed content verbatim."}],
        max_tokens=3000,
    )
    return {"answer": transcript, "summary": summary}
