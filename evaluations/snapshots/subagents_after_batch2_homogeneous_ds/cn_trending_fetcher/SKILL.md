---
name: cn_trending_fetcher
description: **Problem Category**: Fetching real-time trending/hot topic lists from Chinese social media platforms.
entry_file: cn_trending_fetcher.py
---

# cn_trending_fetcher

## Description
**Problem Category**: Fetching real-time trending/hot topic lists from Chinese social media platforms.
**Applicable Questions**: Any request to download/gather trending topics, hot searches, or hot lists with heat values from a Chinese platform (Weibo, Zhihu, Toutiao, Douyin, Baidu).
**Key Features**: Multi-source fetch with fallback (Weibo -> Zhihu -> Toutiao -> Douyin -> Baidu), curl-to-file to bypass output truncation, deterministic parsers for each platform's JSON/HTML schema, LLM fallback extraction, dedupe, top-N selection, writes trending_topics.json.
**Skills Used**: execute_shell_command
**Reasoning Pattern**: iterate sources -> fetch to file -> deterministic parse -> LLM fallback extract -> dedupe -> top-N -> save JSON -> summarize.
**Input Format**: free-text request for trending topics (top N) from a Chinese platform.
**Output Format**: returns {answer, summary}; writes trending_topics.json with {source, top_n, items:[{title,heat}], fetch_log}.

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
