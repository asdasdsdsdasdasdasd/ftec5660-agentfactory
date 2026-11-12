---
name: inspector
description: **Problem Category**: Workspace file/data structure diagnostics.
entry_file: inspector.py
---

# inspector

## Description
**Problem Category**: Workspace file/data structure diagnostics.
**Applicable Questions**: Verifying whether produced files exist, inspecting JSON structure, detecting empty arrays or truncated data, listing workspace files.
**Key Features**: parses a query into file patterns, runs ls/head/json-structure inspection, and uses LLM to summarize data problems.
**Skills Used**: execute_shell_command
**Reasoning Pattern**: plan patterns -> inspect -> LLM diagnose
**Input Format**: free-text inspection request
**Output Format**: returns {answer, summary}.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `inspector.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "inspector", "query": "<your focused sub-question>"}</params>
```
