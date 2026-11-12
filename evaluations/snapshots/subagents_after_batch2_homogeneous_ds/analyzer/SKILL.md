---
name: analyzer
description: **Problem Category**: Sentiment-over-time analysis of collected evidence.
entry_file: analyzer.py
---

# analyzer

## Description
**Problem Category**: Sentiment-over-time analysis of collected evidence.
**Applicable Questions**: Any question asking how public/social sentiment or opinion changed over time on a topic.
**Key Features**: defines time periods from date hints (with year-range fallback), classifies each evidence item's sentiment (positive/negative/neutral) AND assigns it to a period by year mapping, aggregates net-sentiment per period, writes sentiment_timeline.json.
**Skills Used**: execute_shell_command (only for file ops; core logic is LLM)
**Reasoning Pattern**: load evidence -> define periods -> batch-classify (sentiment+period) -> aggregate -> summarize
**Input Format**: free-text request naming input json (default evidence.json)
**Output Format**: returns {answer, summary}; writes sentiment_timeline.json with 'periods_defined', 'timeline' (per-period counts+net_sentiment), 'classified_items'.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `analyzer.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "analyzer", "query": "<your focused sub-question>"}</params>
```
