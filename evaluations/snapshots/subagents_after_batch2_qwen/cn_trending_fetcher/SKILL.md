---
name: cn_trending_fetcher
description: **Problem Category**: Fetching REAL Chinese social-media trending/hot-search data with frequency counts.
entry_file: cn_trending_fetcher.py
---

# cn_trending_fetcher

## Description
**Problem Category**: Fetching REAL Chinese social-media trending/hot-search data with frequency counts.
**Applicable Questions**: Any request to download/gather trending topics or hot-search lists from a Chinese platform (Weibo, Douyin, Baidu) with heat numbers.
**Key Features**: Uses verified-reachable direct platform JSON endpoints (Weibo weibo.com/ajax/side/hotSearch -> data.realtime[].word/.num; Douyin -> data[].word/.hot_value; Baidu top board), deterministic per-platform parsers plus LLM extraction fallback, dedupe + sort desc, writes trending_keywords.json {keyword,count} top-N, supports source preference via LLM parse.
**Skills Used**: execute_shell_command
**Reasoning Pattern**: LLM parse request -> try direct endpoints (python urllib with browser headers/Referer, cert fallback) -> deterministic parse -> LLM fallback -> dedupe/sort -> save JSON.
**Input Format**: free-text request for Chinese trending data (top N, optional platform).
**Output Format**: returns {answer,summary}; writes trending_keywords.json with {source, top_n, items:[{keyword,count}], fetch_log}.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `cn_trending_fetcher.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "cn_trending_fetcher", "query": "<your focused sub-question>"}</params>
```
