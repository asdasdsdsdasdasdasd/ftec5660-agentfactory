---
name: json_file_reader
description: **Problem Category**: Inspecting/verifying JSON data files in the workspace.
entry_file: json_file_reader.py
---

# json_file_reader

## Description
**Problem Category**: Inspecting/verifying JSON data files in the workspace.
**Applicable Questions**: Any task needing to confirm the structure, item count, or sample contents of JSON files produced by other subagents.
**Key Features**: Lists all .json files and reports item counts, samples, and source fields for files shaped as {items:[...]}.
**Skills Used**: execute_shell_command
**Reasoning Pattern**: ls JSON -> load -> summarize item counts/samples.
**Input Format**: free-text verification request.
**Output Format**: returns {answer, summary} with a JSON report of file structures.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `json_file_reader.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "json_file_reader", "query": "<your focused sub-question>"}</params>
```
