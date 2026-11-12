---
name: json_data_inspector
description: **Problem Category**: Verification/inspection of tidy-row JSON datasets.
entry_file: json_data_inspector.py
---

# json_data_inspector

## Description
**Problem Category**: Verification/inspection of tidy-row JSON datasets.
**Applicable Questions**: Any task needing to verify a JSON dataset's completeness, columns, and sample rows before analysis.
**Key Features**: LLM extracts filename from query; prints metrics config, first/last rows, and non-null counts per metric.
**Skills Used**: execute_shell_command
**Reasoning Pattern**: parse filename (LLM) -> load JSON -> print samples + null counts -> LLM summary.
**Input Format**: query naming the JSON file to inspect.
**Output Format**: {answer, summary} with metrics, samples, and completeness counts.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `json_data_inspector.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "json_data_inspector", "query": "<your focused sub-question>"}</params>
```
