---
name: file_inspector
description: **Problem Category**: Read-only filesystem data/file inspection and verification.
entry_file: file_inspector.py
---

# file_inspector

## Description
**Problem Category**: Read-only filesystem data/file inspection and verification.
**Applicable Questions**: Any task needing to confirm file existence, sizes, or print the exact contents of JSON/script files produced by other subagents (e.g., verifying a chart PNG, regression stats, or data files).
**Key Features**: LLM converts a natural-language inspection request into a single safe read-only shell command (ls/cat/stat/wc/head or python one-liners), executes it, and summarizes the factual findings.
**Skills Used**: execute_shell_command
**Reasoning Pattern**: LLM plans inspection command -> run shell -> LLM summarizes file existence/sizes/contents.
**Input Format**: free-text inspection request (which files to list/print/measure).
**Output Format**: {answer, summary}; answer contains raw shell output.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `file_inspector.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "file_inspector", "query": "<your focused sub-question>"}</params>
```
