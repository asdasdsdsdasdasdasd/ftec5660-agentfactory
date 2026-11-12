---
name: anchor_extractor
description: **Problem Category**: Extract ordered, structured lists with real per-item URLs from JavaScript-rendered web pages where plain text fetching misses hyperlinks.
entry_file: anchor_extractor.py
---

# anchor_extractor

## Description
**Problem Category**: Extract ordered, structured lists with real per-item URLs from JavaScript-rendered web pages where plain text fetching misses hyperlinks.
**Applicable Questions**: 'open site X and give the lecture/chapter/product list with their links', any task requiring actual per-item hrefs from a dynamic page.
**Key Features**: Uses Playwright to render the page, scroll to trigger lazy loading, dumps ALL anchors (text + resolved absolute href), then LLM parses them into ordered items with best-matching links; saves debug JSON and markdown. Fully input-driven (URL parsed from query).
**Skills Used**: playwright
**Reasoning Pattern**: parse query->URL/goal -> render with Playwright -> dump anchors + body text -> LLM maps items to hrefs -> write files.
**Input Format**: free-text query containing the target URL and the list to extract.
**Output Format**: {answer, summary}; writes anchors_debug.json and anchors_extract.md.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `anchor_extractor.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "anchor_extractor", "query": "<your focused sub-question>"}</params>
```
