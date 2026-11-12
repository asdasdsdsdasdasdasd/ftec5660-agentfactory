---
name: code_inspector
description: **Problem Category**: Code inspection and verification of Python files in the workspace.
entry_file: code_inspector.py
---

# code_inspector

## Description
**Problem Category**: Code inspection and verification of Python files in the workspace.
**Applicable Questions**: 'Verify that X.py is complete/correct', 'Does this file implement feature Y', 'Find bugs in this script'.
**Key Features**: Locates .py files, extracts AST structure (classes/functions/imports), greps for key components, runs a headless execution test with timeout, and uses an LLM to assess completeness and report concrete findings/bugs.
**Skills Used**: execute_shell_command, call_llm.
**Reasoning Pattern**: locate -> read + AST parse -> grep key features -> run test -> LLM review.
**Input Format**: A query describing what to verify about a Python file.
**Output Format**: dict with answer (file listing/head) and LLM-generated assessment summary.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `code_inspector.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "code_inspector", "query": "<your focused sub-question>"}</params>
```
