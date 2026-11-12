---
name: price_series_volatility_plotter
description: **Problem Category**: Financial/crypto time-series retrieval, plotting, and risk metrics.
entry_file: price_series_volatility_plotter.py
---

# price_series_volatility_plotter

## Description
**Problem Category**: Financial/crypto time-series retrieval, plotting, and risk metrics.
**Applicable Questions**: Any request to search for/plot an asset's historical price and/or compute annualized volatility for a ticker (stock, crypto, ETF, index).
**Key Features**: LLM parses asset+ticker+timeframe from query; Google search corroborates ticker and data source; fetches daily data via yfinance with two Yahoo chart API fallbacks (range and epoch); writes fetch JSON to a file to avoid stdout contamination; matplotlib price chart; annualized volatility from daily log returns using sqrt(252) for trading assets or sqrt(365) for 24/7 crypto.
**Skills Used**: google_search, execute_shell_command.
**Reasoning Pattern**: parse query -> google search ticker -> fetch (yfinance -> Yahoo API x2, file-based JSON handoff) -> LLM plot/vol spec -> matplotlib chart + volatility -> verify.
**Input Format**: free-text request naming an asset, timeframe, and desired outputs.
**Output Format**: {answer, summary}; saves series_data.json, volatility_result.json, price_chart.png.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `price_series_volatility_plotter.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "price_series_volatility_plotter", "query": "<your focused sub-question>"}</params>
```
