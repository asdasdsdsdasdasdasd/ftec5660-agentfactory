---
name: iprobe
description: **Problem Category**: Diagnostic probing of World Bank indicator availability.
entry_file: iprobe.py
---

# iprobe

## Description
**Problem Category**: Diagnostic probing of World Bank indicator availability.
**Applicable Questions**: Checking which World Bank indicator codes return non-null data for a country/year range, or debugging transient 502/timeout behavior of the World Bank API.
**Key Features**: LLM proposes candidate indicator codes from a data request, fetches each via a retried urllib subprocess, reports ROWS/NONNULL counts and sample values so a caller can pick the correct valid indicator.
**Skills Used**: execute_shell_command
**Reasoning Pattern**: LLM list candidate indicators -> per-indicator fetch with retries -> report non-null counts + samples.
**Input Format**: free-text data need (country, concept, years) optionally with specific codes to test.
**Output Format**: returns {answer, summary} with per-indicator ROWS/NONNULL/sample evidence.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `iprobe.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "iprobe", "query": "<your focused sub-question>"}</params>
```
