---
name: raw_shell_runner
description: **Problem Category**: Arbitrary shell/file inspection and execution via LLM-planned commands.
entry_file: raw_shell_runner.py
---

# raw_shell_runner

## Description
**Problem Category**: Arbitrary shell/file inspection and execution via LLM-planned commands.
**Applicable Questions**: 'Show lines X-Y of file', 'Grep for a string and report line numbers', 'Run a compile/test and report output', any task needing direct raw shell output when fixed inspector tools truncate or cannot run custom commands.
**Key Features**: LLM converts the natural-language request into a JSON array of safe non-interactive bash commands, executes them in order, and returns raw combined output verbatim plus an LLM summary. Handles grep, sed/head/tail, wc, py_compile, etc. Avoids destructive commands.
**Skills Used**: execute_shell_command, call_llm.
**Reasoning Pattern**: parse request -> LLM plan commands -> execute -> collect raw outputs -> summarize.
**Input Format**: A natural-language description of what to inspect or run (optionally listing exact commands).
**Output Format**: dict with answer (raw command outputs) and LLM-generated summary.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `raw_shell_runner.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "raw_shell_runner", "query": "<your focused sub-question>"}</params>
```
