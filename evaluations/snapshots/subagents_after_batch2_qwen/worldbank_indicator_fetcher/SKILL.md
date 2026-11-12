---
name: worldbank_indicator_fetcher
description: **Problem Category**: Country-level statistical data acquisition from the World Bank Open Data API.
entry_file: worldbank_indicator_fetcher.py
---

# worldbank_indicator_fetcher

## Description
**Problem Category**: Country-level statistical data acquisition from the World Bank Open Data API.
**Applicable Questions**: Any task needing GDP, life expectancy, population, health expenditure, mortality, or other World Bank indicators for named or auto-selected countries/years.
**Key Features**: LLM parses the request into indicators (with WB codes), countries (ISO3), and year; quotes the api.worldbank.org v2 endpoint; auto-picks the latest common year when unspecified; produces tidy records with all indicators aligned per country; writes wb_data.json.
**Skills Used**: execute_shell_command
**Reasoning Pattern**: LLM parse -> HTTP GET World Bank JSON -> align latest common year -> tidy records -> LLM summary.
**Input Format**: free-text request naming metrics/countries/year (or 'diverse set of N countries').
**Output Format**: {answer, summary}; writes wb_data.json (records, indicators, source, log).

## Skills Used
execute_shell_command

## Usage

**Entry file**: `worldbank_indicator_fetcher.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "worldbank_indicator_fetcher", "query": "<your focused sub-question>"}</params>
```
