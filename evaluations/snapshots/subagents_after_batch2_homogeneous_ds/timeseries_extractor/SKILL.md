---
name: timeseries_extractor
description: **Problem Category**: Numeric time-series extraction from evidence for charting.
entry_file: timeseries_extractor.py
---

# timeseries_extractor

## Description
**Problem Category**: Numeric time-series extraction from evidence for charting.
**Applicable Questions**: Any task needing a clean year-by-year (or ordered) numeric series pulled from a JSON evidence file or inline data to feed a chart.
**Key Features**: LLM plans the source file + metric, loads the JSON, and extracts grounded numeric points (no fabrication), optionally combining single-year figures from multiple sources into one representative trajectory when requested. Writes timeseries.json.
**Skills Used**: execute_shell_command
**Reasoning Pattern**: plan (source+metric) -> load evidence -> LLM extract series -> normalize/validate -> write JSON -> summarize.
**Input Format**: free-text request naming the source file and metric/unit.
**Output Format**: {answer, summary}; writes timeseries.json with 'series', 'metric', 'unit', 'chart_title'.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `timeseries_extractor.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "timeseries_extractor", "query": "<your focused sub-question>"}</params>
```
