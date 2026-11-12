---
name: list_extractor
description: **Problem Category**: Search the web to locate a target page and extract an ordered structured list (topics + links) into a markdown file, with per-item link-recovery fallback via search.
entry_file: list_extractor.py
---

# list_extractor

## Description
**Problem Category**: Search the web to locate a target page and extract an ordered structured list (topics + links) into a markdown file, with per-item link-recovery fallback via search.
**Applicable Questions**: 'search for and open site X, find the syllabus/list, extract first N items with links, save to markdown'.
**Key Features**: LLM plans queries/preferred site/limit/fields; searches and ranks candidate pages; fetches best with fallback; LLM extracts ordered items; recovers missing links via per-topic search and falls back to page URL. Fully input-driven.
**Skills Used**: google_search, read_url_jina
**Reasoning Pattern**: plan -> search -> pick page -> fetch(best+fallback) -> extract list -> recover links -> write markdown.
**Input Format**: free-text research/list-extraction query.
**Output Format**: {answer, summary}; writes a markdown file.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `list_extractor.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "list_extractor", "query": "<your focused sub-question>"}</params>
```
