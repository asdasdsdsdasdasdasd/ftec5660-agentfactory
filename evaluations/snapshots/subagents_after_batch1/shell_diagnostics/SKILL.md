---
name: shell_diagnostics
description: **Problem Category**: Ad-hoc safe shell/OS diagnostics for environment investigation.
entry_file: shell_diagnostics.py
---

# shell_diagnostics

## Description
**Problem Category**: Ad-hoc safe shell/OS diagnostics for environment investigation.
**Applicable Questions**: 'Check if X is installed', 'Find running processes/ports/profiles', 'Inspect a file/DB/cookie store'.
**Key Features**: LLM generates a read-only JSON command list from the goal, executes each via execute_shell_command, and produces a concrete summary. Good for probing browsers, displays, audio devices, processes, ports, and SQLite cookie stores.
**Skills Used**: execute_shell_command.
**Reasoning Pattern**: goal->LLM command list->execute->summarize.
**Input Format**: Natural-language investigation goal.
**Output Format**: dict with answer (JSON map command->output) and LLM summary.

## Skills Used
playwright, execute_shell_command

## Usage

**Entry file**: `shell_diagnostics.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "shell_diagnostics", "query": "<your focused sub-question>"}</params>
```
