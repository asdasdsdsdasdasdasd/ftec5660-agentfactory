---
name: wb_fetcher
description: **Problem Category**: Structured country-indicator time-series data collection via World Bank Open Data API.
entry_file: wb_fetcher.py
---

# wb_fetcher

## Description
**Problem Category**: Structured country-indicator time-series data collection via World Bank Open Data API.
**Applicable Questions**: Any request for annual numeric indicators (GDP, population, education/health spending, etc.) for a country over a year range from authoritative open data.
**Key Features**: LLM maps the request to ISO country code + real World Bank indicator codes + year range, fetches complete series from the World Bank JSON API, then LLM derives requested absolute values (e.g., multiply % of GDP by GDP). Writes clean JSON.
**Skills Used**: google_search, read_url_jina (and stdlib urllib for API)
**Reasoning Pattern**: LLM plan (country/indicators/range) -> fetch each indicator from WB API -> LLM derive final series -> save.
**Input Format**: free-text data request naming country, indicators and year range (optionally WB codes).
**Output Format**: returns {answer, summary}; writes series_data.json with series (name, unit, year->value).

## Skills Used
execute_shell_command

## Usage

**Entry file**: `wb_fetcher.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "wb_fetcher", "query": "<your focused sub-question>"}</params>
```
