---
name: fin_analyzer
description: **Problem Category**: Financial time-series retrieval, statistics, and visualization.
entry_file: fin_analyzer.py
---

# fin_analyzer

## Description
**Problem Category**: Financial time-series retrieval, statistics, and visualization.
**Applicable Questions**: Any request to fetch an asset's historical price data (crypto/stocks/indices), plot a price trend, and compute return statistics such as annualized volatility.
**Key Features**: LLM parses the query into an asset/ticker/period/interval/chart spec; fetches history via Yahoo Finance (yfinance); computes log-return standard deviation and annualized volatility (std x sqrt of annualization factor); renders a matplotlib line chart; writes price_data.json and price_chart.png. Writes raw records to a JSON file instead of stdout to avoid the 5000-char output truncation that silently drops older data points.
**Skills Used**: execute_shell_command
**Reasoning Pattern**: parse spec -> fetch (file-backed) -> compute stats -> plot -> summarize
**Input Format**: free-text request naming the asset, time range, and desired chart/statistic
**Output Format**: {answer, summary}; writes price_data.json, price_chart.png, raw_records.json

## Skills Used
execute_shell_command

## Usage

**Entry file**: `fin_analyzer.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "fin_analyzer", "query": "<your focused sub-question>"}</params>
```
