---
name: trending_keyword_fetcher
description: **Problem Category**: Fetching real trending keyword FREQUENCY data from public social-media/trending APIs.
entry_file: trending_keyword_fetcher.py
---

# trending_keyword_fetcher

## Description
**Problem Category**: Fetching real trending keyword FREQUENCY data from public social-media/trending APIs.
**Applicable Questions**: Any request to download/gather trending keywords, hashtags, or topics with counts from a social platform or public trending source (Mastodon/fediverse, Wikimedia pageviews, etc.).
**Key Features**: LLM plans candidate public JSON endpoints; fetches to FILES via curl to bypass the 5000-char shell truncation; deterministically parses the Mastodon schema (tags history.uses, statuses tags) plus LLM extraction; aggregates/dedupes across multiple instances; normalizes singular/plural; writes trending_keywords.json.
**Skills Used**: execute_shell_command
**Reasoning Pattern**: plan sources -> fetch to file -> LLM/deterministic extract -> aggregate+dedupe -> top-N -> save JSON -> summarize.
**Input Format**: free-text request for trending keyword frequency data (top N).
**Output Format**: returns {answer, summary}; writes trending_keywords.json with {source, top_n, items:[{keyword,count}], fetch_log}.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `trending_keyword_fetcher.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "trending_keyword_fetcher", "query": "<your focused sub-question>"}</params>
```
