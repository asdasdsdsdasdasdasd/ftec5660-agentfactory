---
name: keyword_bar_chart
description: **Problem Category**: Rendering a labeled bar chart from a JSON file of {keyword,count} rows.
entry_file: keyword_bar_chart.py
---

# keyword_bar_chart

## Description
**Problem Category**: Rendering a labeled bar chart from a JSON file of {keyword,count} rows.
**Applicable Questions**: Any request to visualize ranked keyword/tag/label frequencies as a bar chart from a saved JSON dataset.
**Key Features**: LLM picks the JSON file/fields/title/axes; robust row loading from items/list shapes; dedupe + sort desc + top-N; horizontal or vertical bars; auto-detects CJK fonts so non-Latin labels render; verifies PNG output.
**Skills Used**: execute_shell_command
**Reasoning Pattern**: plan->load JSON->normalize/sort->write chart_items.json->generate matplotlib script->run->verify PNG.
**Input Format**: free-text chart request referencing a saved keyword-frequency JSON.
**Output Format**: returns {answer, summary}; writes trending_keywords_bar_chart.png, chart_items.json, make_bar_chart.py.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `keyword_bar_chart.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "keyword_bar_chart", "query": "<your focused sub-question>"}</params>
```
