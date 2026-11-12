import json
import re
from llm import call_llm
from tools import execute_shell_command


def main(query: str) -> dict:
    evidence = []

    plan = call_llm(
        system="You are a system diagnostics expert. Given an environment investigation goal, produce a JSON array of safe, read-only bash commands (no rm, no destructive ops) that gather the needed evidence. Each command short, prints clear output.",
        messages=[{"role": "user", "content": f"Investigation goal: {query}\n\nReturn ONLY a JSON array of command strings. Example: [\"python --version\", \"which ffmpeg\"]. Max 15 commands."}],
        max_tokens=1200,
    )
    cmds = []
    try:
        m = re.search(r"\[.*\]", plan, re.DOTALL)
        if m:
            cmds = json.loads(m.group(0))
    except Exception as e:
        evidence.append(f"Could not parse commands: {e}")

    # Prepend robust Python/binary probes that avoid fragile LLM-generated quoting
    pkg_probe = (
        "python -c \"import importlib.util as u;import sys;"
        "pkgs=['pydub','gTTS','pyttsx3','numpy','scipy','soundfile','librosa','mutagen','TTS','pyaudio','simpleaudio'];"
        "[print(p+':',('OK' if u.find_spec(p) else 'MISSING')) for p in pkgs]\" 2>&1"
    )
    bin_probe = (
        "for t in espeak espeak-ng festival flite say pico2wave ffmpeg lame sox; do "
        "p=$(command -v $t 2>/dev/null); if [ -n \"$p\" ]; then echo \"$t: $p\"; else echo \"$t: NOT FOUND\"; fi; done"
    )
    net_probe = "python -c 'import urllib.request; urllib.request.urlopen(\"https://pypi.org\", timeout=6); print(\"INTERNET: OK\")' 2>&1 | tail -1"
    base_cmds = ["python --version", pkg_probe, bin_probe, net_probe]
    cmds = base_cmds + [c for c in cmds if c not in base_cmds]

    if not cmds:
        cmds = ["python --version", "pip --version"]

    outputs = {}
    for c in cmds:
        try:
            out = execute_shell_command(c)
        except Exception as e:
            out = f"ERROR: {e}"
        outputs[c] = out[:2000]
        evidence.append(f"$ {c}\n{out[:2000]}")

    summary = call_llm(
        system="You are a diagnostics reporter. Summarize environment findings clearly and answer the goal directly.",
        messages=[{"role": "user", "content": f"Goal: {query}\n\nCommand outputs:\n" + "\n\n".join(evidence) + "\n\nWrite a SUMMARY (100-1500 words) listing what was found and the direct answer."}],
        max_tokens=2000,
    )

    return {"answer": json.dumps(outputs)[:4000], "summary": summary}
