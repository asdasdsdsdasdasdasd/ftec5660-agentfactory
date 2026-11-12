---
name: focus_audio_producer
description: **Problem Category**: Generating background/focus/ambient audio with voice prompts at SPECIFIC timeline positions. **Applicable Questions**: 'Create a focus/ambient audio with prompts at the beginning...
entry_file: focus_audio_producer.py
---

# focus_audio_producer

## Description
**Problem Category**: Generating background/focus/ambient audio with voice prompts at SPECIFIC timeline positions. **Applicable Questions**: 'Create a focus/ambient audio with prompts at the beginning and midpoint', 'Make a long background track with sparse narration at set timestamps'. **Key Features**: LLM plan with per-section position_ratio (0.0-1.0); gTTS synthesis; synthetic rain/waves/wind ambient + subtle steady rhythm/music bed (sine-bell pulse + drone pad); numpy timeline assembly placing each voice segment at its exact ratio; PyAV MP3 export; duration/placement verification. **Skills Used**: execute_shell_command, call_llm. **Reasoning Pattern**: plan(query)->JSON(sections with position_ratio, ambient, rhythm, duration) -> gTTS -> decode voice to SR -> build ambient+rhythm bed -> overlay voice at ratios -> normalize/fade -> PyAV encode -> tag -> verify. **Input Format**: Natural-language audio request specifying duration, ambient, rhythm, and when prompts should play. **Output Format**: dict with answer (path/size/duration/placement) and LLM summary. **Improved From**: audio_producer placed all voice prompts sequentially from the start (midpoint prompt played at ~90s instead of the true midpoint). This version places each section at an LLM-specified position_ratio along the full timeline and adds a steady rhythm/music layer.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `focus_audio_producer.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "focus_audio_producer", "query": "<your focused sub-question>"}</params>
```
