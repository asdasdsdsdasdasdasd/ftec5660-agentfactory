---
name: guided_ambient_audio
description: **Problem Category**: Generating complete ambient/guided background audio files (focus, meditation, relaxation, sleep) with a specific voice, layered nature sounds, background music, and timed voice p...
entry_file: guided_ambient_audio.py
---

# guided_ambient_audio

## Description
**Problem Category**: Generating complete ambient/guided background audio files (focus, meditation, relaxation, sleep) with a specific voice, layered nature sounds, background music, and timed voice prompts, exported as MP3.
**Applicable Questions**: 'Create a focus/relaxation audio saved as X.mp3 with rain + subtle music + a calm male voice prompt at start and midpoint', 'Make an ambient audio with waves and a voice every 5 minutes', any request combining TTS voice + procedural ambient/music + MP3 export.
**Key Features**: LLM parses the query into a JSON plan (filename, duration, voice gender, prompt timings+text, ambient layers, background music, rhythm, per-layer volumes); installs edge-tts+mutagen; picks a real male/female NEURAL voice (en-US-GuyNeural etc.) that supports gender selection (unlike gTTS); synthesizes brief prompts; procedurally generates rain/waves/wind/birds/fire ambient noise and a separate harmonic background-music bed; applies steady-rhythm amplitude modulation; overlays voice prompts at LLM-determined absolute timestamps (e.g. beginning+midpoint only, not throughout); mixes with configurable low volumes; exports MP3 via PyAV (bundled ffmpeg, no binary needed); tags with mutagen; verifies duration.
**Skills Used**: execute_shell_command, call_llm.
**Reasoning Pattern**: plan(query)->JSON -> ensure edge-tts/deps -> pick voice matching gender -> synth prompts -> numpy ambient layers + music bed + rhythm -> overlay prompts at timestamps -> PyAV encode -> mutagen tag/verify.
**Input Format**: Natural-language audio request (topic, duration/range, voice gender/mood, ambient sounds, background music, prompt placement, filename).
**Output Format**: dict with answer (output path, size, duration, voice, prompt count/timestamps) and LLM summary. Solves the male-voice requirement that gTTS-based tools cannot.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `guided_ambient_audio.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "guided_ambient_audio", "query": "<your focused sub-question>"}</params>
```
