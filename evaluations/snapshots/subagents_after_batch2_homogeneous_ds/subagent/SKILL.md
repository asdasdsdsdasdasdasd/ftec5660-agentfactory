---
name: subagent
description: **Problem Category**: Multi-country, multi-indicator time-series data collection via World Bank Open Data API.
entry_file: subagent.py
---

# subagent

## Description
**Problem Category**: Multi-country, multi-indicator time-series data collection via World Bank Open Data API.
**Applicable Questions**: Any request for GDP, GDP per capita, life expectancy, population, education/health spending, or other World Development Indicators across MULTIPLE countries and/or a year range from authoritative open data.
**Key Features**: LLM parses the request into ISO country codes, real World Bank indicator codes, and a year range; fetches complete series via the public World Bank JSON API (supports semicolon-separated multi-country queries); writes wb_multi_data.json with full series plus latest-value-per-country summary. Handles the multi-country case that single-country fetchers miss.
**Skills Used**: execute_shell_command, call_llm.
**Reasoning Pattern**: LLM plan (countries/indicators/range) -> fetch each indicator from WB API -> compute latest values -> save JSON -> LLM summary.
**Input Format**: Free-text data request naming countries, indicators, and year range.
**Output Format**: returns {answer, summary}; writes wb_multi_data.json (indicators with per-country year->value data and latest_values).

## Skills Used
execute_shell_command

## Usage

**Entry file**: `subagent.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "subagent", "query": "<your focused sub-question>"}</params>
```
