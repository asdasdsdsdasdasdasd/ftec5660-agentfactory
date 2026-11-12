---
name: browser_task_agent
description: **Problem Category**: Web automation that must leave the browser OPEN after completion (e.g., 'play this song and keep the browser open so I can listen').
entry_file: browser_task_agent.py
---

# browser_task_agent

## Description
**Problem Category**: Web automation that must leave the browser OPEN after completion (e.g., 'play this song and keep the browser open so I can listen').
**Applicable Questions**: 'Open site X and do Y, then leave the browser open', 'Play <song/video> and keep it running'.
**Key Features**: Spawns a DETACHED background keeper process (nohup) that launches a persistent non-headless Chromium on DISPLAY=:1, runs an LLM-driven element-discovery+action loop (click/type/scroll/goto/done) with popup handling, writes final state JSON, then sleeps forever holding the browser open (SingletonLock alive). Foreground polls state and reports.
**Skills Used**: playwright, execute_shell_command.
**Reasoning Pattern**: write keeper script -> spawn detached -> LLM action loop over discovered elements -> dump state -> keep browser alive.
**Input Format**: Natural-language web task; browser assumed already logged in.
**Output Format**: dict with answer (keeper PID + final state) and summary.

## Skills Used
playwright, execute_shell_command

## Usage

**Entry file**: `browser_task_agent.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "browser_task_agent", "query": "<your focused sub-question>"}</params>
```
