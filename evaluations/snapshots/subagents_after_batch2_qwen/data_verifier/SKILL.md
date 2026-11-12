---
name: data_verifier
description: **Problem Category**: JSON data-file content verification and summarization.
entry_file: data_verifier.py
---

# data_verifier

## Description
**Problem Category**: JSON data-file content verification and summarization.
**Applicable Questions**: Any task needing to inspect a workspace JSON file's full structure and values (e.g., verify a collected data series before plotting).
**Key Features**: LLM picks the best-matching JSON file for the request (or all), dumps pretty-printed full contents (bounded), and summarizes structure/values. Note: globs only top-level *.json files, not subdirectories; use file_inspector for nested paths.
**Skills Used**: execute_shell_command
**Reasoning Pattern**: list JSON -> LLM picks file -> dump contents -> LLM summarizes.
**Input Format**: free-text verification request naming the data to inspect.
**Output Format**: {answer, summary}; answer contains pretty-printed JSON contents.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `data_verifier.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "data_verifier", "query": "<your focused sub-question>"}</params>
```
