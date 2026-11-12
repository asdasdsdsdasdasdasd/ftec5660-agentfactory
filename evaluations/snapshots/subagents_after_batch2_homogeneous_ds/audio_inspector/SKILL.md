---
name: audio_inspector
description: **Problem Category**: Audio QA / verification. **Applicable Questions**: 'Where in this audio do voice prompts occur?', 'Verify audio duration/bitrate and confirm sustained content', 'Check if voice i...
entry_file: audio_inspector.py
---

# audio_inspector

## Description
**Problem Category**: Audio QA / verification. **Applicable Questions**: 'Where in this audio do voice prompts occur?', 'Verify audio duration/bitrate and confirm sustained content', 'Check if voice is at the midpoint of a track'. **Key Features**: real duration/bitrate/channels via mutagen; per-30s RMS loudness-envelope analysis via PyAV decode+numpy to locate louder (voice/event) regions vs ambient floor and confirm sustained audio without silent gaps. **Skills Used**: execute_shell_command, call_llm. **Reasoning Pattern**: parse filename -> mutagen info -> decode & compute 1s RMS -> bin per 30s -> threshold to flag loud regions -> LLM summary of placement relative to total duration. **Input Format**: Natural-language inspection request naming the audio file (defaults to focus_music.mp3). **Output Format**: dict with answer (file/size/duration/voice_bin_starts) and LLM summary.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `audio_inspector.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "audio_inspector", "query": "<your focused sub-question>"}</params>
```
