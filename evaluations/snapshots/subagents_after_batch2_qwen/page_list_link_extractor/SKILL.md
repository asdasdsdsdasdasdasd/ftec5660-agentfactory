---
name: page_list_link_extractor
description: **Problem Category**: Web research that opens a target page and extracts a list of items with both labels and their hyperlinks.
entry_file: page_list_link_extractor.py
---

# page_list_link_extractor

## Description
**Problem Category**: Web research that opens a target page and extracts a list of items with both labels and their hyperlinks.
**Applicable Questions**: 'Search for and open site X, find the syllabus/lecture list/table, and output the items with their corresponding links, save to markdown', any 'extract list entries with URLs from a page' task.
**Key Features**: LLM-plans search queries + preferred domain + items to extract; searches (with site: restriction) and ranks candidates; opens the best page with Playwright to extract ALL rendered anchor hrefs (with jina fallback for text); feeds page text + anchors to an LLM that maps requested list items to number/topic/link (using only real hrefs, never invented); writes a markdown table to a file. Handles JS-rendered lists that plain text fetch misses.
**Skills Used**: google_search, read_url_jina, playwright
**Reasoning Pattern**: plan -> search -> rank -> open page (Playwright anchors) -> LLM map items to topics+links -> write markdown -> summarize
**Input Format**: free-text research task/query describing the page and the list of items to extract.
**Output Format**: returns {answer, summary}; writes a markdown file with a table of items (number, topic, link).

## Skills Used
google_search, read_url_jina, playwright

## Usage

**Entry file**: `page_list_link_extractor.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "page_list_link_extractor", "query": "<your focused sub-question>"}</params>
```
