---
name: md_writer
description: **Problem Category**: Write a clean markdown file (table + hyperlinked detail list) from structured topics+links content, with self-verification.
entry_file: md_writer.py
---

# md_writer

## Description
**Problem Category**: Write a clean markdown file (table + hyperlinked detail list) from structured topics+links content, with self-verification.
**Applicable Questions**: any task ending with 'save these results to a markdown file'.
**Key Features**: LLM parses content/filename/title/items, writes a formatted .md, then cats it back via shell to verify. Fully input-driven.
**Skills Used**: execute_shell_command
**Reasoning Pattern**: parse -> build markdown -> write file -> verify by cat.
**Input Format**: free-text content plus output filename instructions.
**Output Format**: {answer with verify output, summary}; writes the .md file.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `md_writer.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "md_writer", "query": "<your focused sub-question>"}</params>
```
