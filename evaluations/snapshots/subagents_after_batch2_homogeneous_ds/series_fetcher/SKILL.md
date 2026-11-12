---
name: series_fetcher
description: **Problem Category**: Numeric paired time-series data acquisition from public APIs (World Bank, FRED) with robust retry.
entry_file: series_fetcher.py
---

# series_fetcher

## Description
**Problem Category**: Numeric paired time-series data acquisition from public APIs (World Bank, FRED) with robust retry.
**Applicable Questions**: Any request to collect two or more aligned annual numeric series (e.g. expenditure vs GDP, indicator comparisons) by year and output a paired JSON for plotting/regression.
**Key Features**: LLM plans series-to-source mappings (World Bank indicator codes / FRED ids), fetches each via a self-contained urllib subprocess (avoids execute_shell_command 5000-char stdout truncation), retries on transient 502/timeouts with backoff, guarantees output-file write, aligns by year, writes paired_series.json. Known-good World Bank codes documented.
**Skills Used**: execute_shell_command
**Reasoning Pattern**: LLM plan sources -> per-series urllib fetch (retry) -> parse points -> align by year -> write JSON -> summarize.
**Input Format**: free-text request naming the two series, entity/country, units, and year range.
**Output Format**: returns {answer, summary}; writes paired_series.json with rows/series_names/n_rows.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `series_fetcher.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "series_fetcher", "query": "<your focused sub-question>"}</params>
```
