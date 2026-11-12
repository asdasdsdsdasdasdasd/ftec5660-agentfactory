---
name: site_list_extractor
description: **Problem Category**: Web page structured-list extraction with links.
entry_file: site_list_extractor.py
---

# site_list_extractor

## Description
**Problem Category**: Web page structured-list extraction with links.
**Applicable Questions**: Any request to locate a website/page via web search and extract an ordered list of items WITH their corresponding links (e.g. lecture list, syllabus, course topics, schedule rows, menu items, table rows), then save results to a markdown file.
**Key Features**: Fully LLM-driven; parses the query into search_query/page_hints/item_count/item_type/output_filename; uses google_search to find the target URL; fetches text via read_url_jina and scrapes anchors + tables via Playwright; an LLM then selects the contiguous ordered items, resolves relative links to absolute, and writes a clean markdown table. Handles both DOM-link and text-only list pages.
**Skills Used**: google_search, read_url_jina, playwright, execute_shell_command
**Reasoning Pattern**: parse query -> search -> pick URL -> fetch text + scrape DOM -> LLM selects/cleans N items -> write markdown -> LLM summary
**Input Format**: free-text request naming the target site/page and what list to extract (with item count).
**Output Format**: returns {answer, summary}; writes a markdown file (name derived from query) with a table of #/topic/link, plus source URL and page title.

## Skills Used
google_search, read_url_jina, playwright, execute_shell_command

## Usage

**Entry file**: `site_list_extractor.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "site_list_extractor", "query": "<your focused sub-question>"}</params>
```
