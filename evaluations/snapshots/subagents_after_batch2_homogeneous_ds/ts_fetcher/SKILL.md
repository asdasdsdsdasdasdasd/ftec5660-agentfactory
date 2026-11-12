---
name: ts_fetcher
description: **Problem Category**: Web-based numeric time-series extraction for arbitrary indicators.
entry_file: ts_fetcher.py
---

# ts_fetcher

## Description
**Problem Category**: Web-based numeric time-series extraction for arbitrary indicators.
**Applicable Questions**: Any task needing year-by-year numeric values (e.g., budget, expenditure, statistics) scraped from web pages/tables when a structured API is unavailable.
**Key Features**: LLM plans diverse search queries, runs web search, fetches pages, per-document LLM extraction of year->value series, fuzzy-matches series names, then LLM normalizes units across sources. Writes series_data.json.
**Skills Used**: google_search, read_url_jina
**Reasoning Pattern**: plan series+queries -> search -> fetch -> per-doc numeric extraction -> unit normalization -> save.
**Input Format**: free-text description of indicators, year range, and preferred sources.
**Output Format**: returns {answer, summary}; writes series_data.json with normalized series (name, unit, year->value).

## Skills Used
execute_shell_command

## Usage

**Entry file**: `ts_fetcher.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "ts_fetcher", "query": "<your focused sub-question>"}</params>
```
