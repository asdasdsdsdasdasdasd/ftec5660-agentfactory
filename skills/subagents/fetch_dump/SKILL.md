---
name: fetch_dump
description: **Problem Category**: Page-content verification and fact-checking of a specific URL.
entry_file: fetch_dump.py
---

# fetch_dump

## Description
**Problem Category**: Page-content verification and fact-checking of a specific URL.
**Applicable Questions**: 'Does this page actually say X?', 'Fetch this URL and tell me its description / list its repositories / quote the bio', verifying whether a fetched page contains claimed information.
**Key Features**: Extracts a URL from the query, fetches full page text via read_url_jina, and answers the user's question strictly from page content using an LLM instructed to quote exact strings and flag garbled/truncated/missing info (useful for catching hallucinations in downstream extraction).
**Skills Used**: read_url_jina.
**Reasoning Pattern**: extract URL -> fetch -> LLM answer grounded in page text -> LLM summary.
**Input Format**: free-text query containing a URL plus a question.
**Output Format**: returns {answer, summary}.

## Skills Used
execute_shell_command, google_search

## Usage

**Entry file**: `fetch_dump.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "fetch_dump", "query": "<your focused sub-question>"}</params>
```
