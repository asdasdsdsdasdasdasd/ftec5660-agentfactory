---
name: fetch_debug_probe
description: **Problem Category**: Diagnostic probing of Yahoo Finance/yfinance price-data availability.
entry_file: fetch_debug_probe.py
---

# fetch_debug_probe

## Description
**Problem Category**: Diagnostic probing of Yahoo Finance/yfinance price-data availability.
**Applicable Questions**: When a price-data fetch returns empty/truncated results and you need to verify whether yfinance and the direct Yahoo chart API actually return data for a ticker.
**Key Features**: LLM extracts a ticker from input, runs both yfinance and direct Yahoo chart API fetches, and reports raw point counts, date ranges, and errors to isolate fetch vs parsing failures.
**Skills Used**: execute_shell_command.
**Reasoning Pattern**: extract ticker -> run dual fetch probe -> report counts/ranges/errors.
**Input Format**: a ticker or free-text containing one.
**Output Format**: {answer (raw output), summary}.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `fetch_debug_probe.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "fetch_debug_probe", "query": "<your focused sub-question>"}</params>
```
