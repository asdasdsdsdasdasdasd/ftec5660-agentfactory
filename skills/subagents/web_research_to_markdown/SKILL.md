---
name: web_research_to_markdown
description: **Problem Category**: Web research that locates a target page (optionally on a preferred site like Wikipedia), extracts requested content, and writes a structured markdown report to a file.
entry_file: web_research_to_markdown.py
---

# web_research_to_markdown

## Description
**Problem Category**: Web research that locates a target page (optionally on a preferred site like Wikipedia), extracts requested content, and writes a structured markdown report to a file.
**Applicable Questions**: Tasks like 'search for and open site X, extract/summarize Y, save to markdown', any research-and-report generation with a specified source site or target article.
**Key Features**: LLM-plans search queries and preferred domain, runs web search (including site: restriction), ranks/deduplicates candidate URLs, fetches the best page with fallback to others, LLM-extracts core definition + summary + key points, writes a .md file to a relative path. Fully input-driven (no hardcoded topics/URLs).
**Skills Used**: google_search (search_serper), read_url_jina
**Reasoning Pattern**: plan -> search -> rank -> fetch(best+fallback) -> extract -> write markdown -> summarize
**Input Format**: free-text research task/query.
**Output Format**: returns {answer, summary}; writes a markdown file (filename chosen by planner).

## Skills Used
google_search, read_url_jina

## Usage

**Entry file**: `web_research_to_markdown.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "web_research_to_markdown", "query": "<your focused sub-question>"}</params>
```
