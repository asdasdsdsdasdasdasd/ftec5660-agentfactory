---
name: reporter
description: **Problem Category**: Report + chart generation from a sentiment timeline.
entry_file: reporter.py
---

# reporter

## Description
**Problem Category**: Report + chart generation from a sentiment timeline.
**Applicable Questions**: Any request to visualize a sentiment/trend timeline and produce a structured markdown report with Discussion and Summary.
**Key Features**: renders a two-panel matplotlib chart (net-sentiment trend line + stacked positive/neutral/negative composition), and writes a markdown report with Introduction, Methodology, Trend Analysis, Discussion, and a separately-generated Summary (so truncation cannot drop it). Handles 'Unknown' bucket.
**Skills Used**: execute_shell_command (runs matplotlib script)
**Reasoning Pattern**: load timeline+evidence -> build chart -> LLM writes report body -> separate LLM writes Summary -> assemble and save
**Input Format**: free-text request; parses file names from it
**Output Format**: returns {answer, summary}; writes sentiment_trend.png and report.md.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `reporter.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "reporter", "query": "<your focused sub-question>"}</params>
```
