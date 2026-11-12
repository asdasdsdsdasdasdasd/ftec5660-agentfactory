---
name: yf_debug
description: **Problem Category**: Diagnostic probing of Yahoo Finance / yfinance data availability.
entry_file: yf_debug.py
---

# yf_debug

## Description
**Problem Category**: Diagnostic probing of Yahoo Finance / yfinance data availability.
**Applicable Questions**: When a price-data fetch returns empty or truncated results and you need to determine whether the data source is reachable and complete.
**Key Features**: Compares yf.download (period-based), Ticker.history, and the direct Yahoo chart API, reporting record counts and date ranges for each.
**Skills Used**: execute_shell_command
**Reasoning Pattern**: run three fetch methods -> report lengths and head/tail dates
**Input Format**: free-text description of what to probe
**Output Format**: {answer, summary} with the raw probe output

## Skills Used
execute_shell_command

## Usage

**Entry file**: `yf_debug.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "yf_debug", "query": "<your focused sub-question>"}</params>
```
