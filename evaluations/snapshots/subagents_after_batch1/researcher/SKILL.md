---
name: researcher
description: **Problem Category**: Web evidence collection for arbitrary research topics.
entry_file: researcher.py
---

# researcher

## Description
**Problem Category**: Web evidence collection for arbitrary research topics.
**Applicable Questions**: Any task requiring gathering textual evidence, quotes, discussions, opinions or data about a topic from online sources.
**Key Features**: LLM plans diverse search queries, runs web search, fetches full pages, extracts structured evidence per-document (text, date_hint, sentiment_hint) to avoid truncation, writes evidence.json. Uses per-document extraction with robust JSON parsing and fallbacks.
**Skills Used**: google_search (search_serper), read_url_jina
**Reasoning Pattern**: plan queries -> search -> dedupe -> fetch -> per-doc extract -> summarize
**Input Format**: a free-text research topic/question string
**Output Format**: returns {answer, summary}; writes evidence.json with 'evidence' list, 'focus', 'documents', 'topic_summary'.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `researcher.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "researcher", "query": "<your focused sub-question>"}</params>
```
