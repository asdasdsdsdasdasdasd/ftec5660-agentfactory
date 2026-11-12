---
name: audio_transcriber
description: **Problem Category**: Speech-to-text transcription of audio files (MP3/WAV/etc.).
entry_file: audio_transcriber.py
---

# audio_transcriber

## Description
**Problem Category**: Speech-to-text transcription of audio files (MP3/WAV/etc.).
**Applicable Questions**: 'Transcribe this audio', 'What is said in <file>.mp3', extracting spoken instructions from a recording.
**Key Features**: Parses audio path from query via LLM, verifies file, installs faster-whisper (falls back to openai-whisper), uses imageio-ffmpeg bundled binary or passes original audio directly when system ffmpeg is missing, transcribes and returns verbatim text.
**Skills Used**: execute_shell_command.
**Reasoning Pattern**: parse(query)->ensure backend+ffmpeg->transcribe (faster-whisper then openai-whisper fallback)->return text.
**Input Format**: Natural-language request containing the audio file path.
**Output Format**: dict with answer (verbatim transcript) and LLM summary.

## Skills Used
playwright, execute_shell_command

## Usage

**Entry file**: `audio_transcriber.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "audio_transcriber", "query": "<your focused sub-question>"}</params>
```
