---
name: reader
description: **Problem Category**: Verification of produced report/image artifacts.
entry_file: reader.py
---

# reader

## Description
**Problem Category**: Verification of produced report/image artifacts.
**Applicable Questions**: Confirming a markdown report contains required section headers, checking image dimensions/validity, reading tails of files.
**Key Features**: extracts filenames from query, checks existence, greps markdown headers, gets image dimensions via PIL, uses LLM to answer the verification question.
**Skills Used**: execute_shell_command
**Reasoning Pattern**: extract files -> inspect headers/image -> LLM verdict
**Input Format**: free-text verification request naming files
**Output Format**: returns {answer, summary}.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `reader.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "reader", "query": "<your focused sub-question>"}</params>
```
