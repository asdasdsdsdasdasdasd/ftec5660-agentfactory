---
name: code_generator_tester
description: **Problem Category**: Code generation and validation for any programming task.
entry_file: code_generator_tester.py
---

# code_generator_tester

## Description
**Problem Category**: Code generation and validation for any programming task.
**Applicable Questions**: 'Write a program/script/game that does X', 'Implement a tool that...', any request to produce runnable code.
**Key Features**: Plans implementation via LLM, checks environment for available libraries, generates complete self-contained Python code, validates with py_compile and AST parsing, retries up to 4 times with error feedback, saves validated program to solution.py.
**Skills Used**: execute_shell_command, call_llm.
**Reasoning Pattern**: plan -> env check -> generate -> validate syntax -> validate AST -> retry on failure -> save + summarize.
**Input Format**: A natural-language description of the program to build.
**Output Format**: dict with answer (path + status) and LLM-generated summary.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `code_generator_tester.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "code_generator_tester", "query": "<your focused sub-question>"}</params>
```
