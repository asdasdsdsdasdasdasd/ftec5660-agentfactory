---
name: chart_verify
description: **Problem Category**: QA-verifying generated chart images and their source data files.
entry_file: chart_verify.py
---

# chart_verify

## Description
**Problem Category**: QA-verifying generated chart images and their source data files.
**Applicable Questions**: Any task where a bar/line/etc chart PNG was generated and you must confirm validity, dimensions, row counts and correct CJK font rendering.
**Key Features**: Validates PNG magic number and dimensions, checks row counts in referenced JSON data files, detects CJK-capable matplotlib fonts (Noto CJK, IPAGothic, WenQuanYi, SimHei, etc.) to ensure non-Latin labels are not tofu.
**Skills Used**: execute_shell_command
**Reasoning Pattern**: locate PNG -> read header/dimensions -> check fonts -> validate data rows -> LLM QA summary.
**Input Format**: free-text verification request naming the chart file.
**Output Format**: returns {answer,summary} with PNG validity/dimensions, row counts and font availability.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `chart_verify.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "chart_verify", "query": "<your focused sub-question>"}</params>
```
