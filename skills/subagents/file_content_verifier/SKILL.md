---
name: file_content_verifier
description: **Problem Category**: File existence and content verification.
entry_file: file_content_verifier.py
---

# file_content_verifier

## Description
**Problem Category**: File existence and content verification.
**Applicable Questions**: 'Verify file X exists', 'show contents of file Y', 'check if a generated output file was created correctly'.
**Key Features**: LLM parses target filename and verification goal from the query, uses shell commands (ls, cat, wc, find) to confirm existence and display content, LLM generates factual answer and summary.
**Skills Used**: execute_shell_command.
**Reasoning Pattern**: parse query -> shell inspect (ls/cat/wc/find) -> LLM-answer -> LLM-summary.
**Input Format**: free-text request naming a file and what to verify.
**Output Format**: returns {answer, summary} describing whether the file exists and its contents.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `file_content_verifier.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "file_content_verifier", "query": "<your focused sub-question>"}</params>
```
