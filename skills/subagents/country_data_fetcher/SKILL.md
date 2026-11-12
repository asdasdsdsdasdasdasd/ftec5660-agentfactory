---
name: country_data_fetcher
description: **Problem Category**: Country-level environmental/economic timeseries data acquisition from Our World in Data.
entry_file: country_data_fetcher.py
---

# country_data_fetcher

## Description
**Problem Category**: Country-level environmental/economic timeseries data acquisition from Our World in Data.
**Applicable Questions**: Any task needing CO2 emissions, energy, or renewable-share data for specific countries/years from a reliable public source.
**Key Features**: LLM parses query to pick countries, metrics, and year range; downloads OWID CO2 and/or energy CSVs from GitHub via curl; extracts tidy rows with pandas to fetched_data.json.
**Skills Used**: execute_shell_command
**Reasoning Pattern**: parse query (LLM) -> download CSVs -> pandas filter/extract -> write tidy JSON.
**Input Format**: free-text query naming metrics, countries, year range.
**Output Format**: {answer, summary}; writes fetched_data.json (rows, metrics, n_rows).

## Skills Used
execute_shell_command

## Usage

**Entry file**: `country_data_fetcher.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "country_data_fetcher", "query": "<your focused sub-question>"}</params>
```
