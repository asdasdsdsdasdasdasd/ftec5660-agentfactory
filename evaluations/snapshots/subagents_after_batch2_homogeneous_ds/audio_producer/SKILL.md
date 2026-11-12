---
name: audio_producer
description: **Problem Category**: Generating complete narrated/guided audio files (meditations, relaxations, sleep stories, affirmations) with ambient sound and MP3 export.
entry_file: audio_producer.py
---

# audio_producer

## Description
**Problem Category**: Generating complete narrated/guided audio files (meditations, relaxations, sleep stories, affirmations) with ambient sound and MP3 export.
**Applicable Questions**: 'Create a guided meditation/relaxation/bedtime audio', 'Make a narrated audio with background music/rain/waves', 'Generate a 15-minute voice-over audio saved as X.mp3'.
**Key Features**: LLM parses the request and writes a full multi-section script (intro/breathing/body-scan/visualization/closing or whatever the user specifies) driven entirely by the query; installs gTTS+mutagen; synthesizes each section via gTTS (slow mode for calm pace); generates synthetic ambient (rain/waves/wind) with numpy; decodes mp3 and mixes voice+ambient via PyAV (bundled ffmpeg libs, no ffprobe/ffmpeg binary required); pads to a minimum duration from target_minutes; exports MP3 and tags it; verifies size/duration.
**Skills Used**: execute_shell_command, call_llm.
**Reasoning Pattern**: plan(query)->JSON(script+sections+ambient+duration) -> ensure deps -> gTTS per section -> numpy ambient -> PyAV decode/mix/encode -> duration verification -> tag.
**Input Format**: Natural-language audio request (topic, desired duration, voice mood, ambient, filename).
**Output Format**: dict with answer (output path, size, duration, method) and LLM summary.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `audio_producer.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "audio_producer", "query": "<your focused sub-question>"}</params>
```
