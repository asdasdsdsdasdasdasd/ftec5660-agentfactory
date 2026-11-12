---
name: plot_trending_bar
description: **Problem Category**: Visualizing a ranked list of trending/keyword items with numeric values as a bar chart.
entry_file: plot_trending_bar.py
---

# plot_trending_bar

## Description
**Problem Category**: Visualizing a ranked list of trending/keyword items with numeric values as a bar chart.
**Applicable Questions**: Any request to plot top-N trending topics, keywords, or ranked lists (with counts/heat) from a workspace JSON file into a horizontal bar chart PNG.
**Key Features**: Auto-discovers a workspace JSON containing an items list, extracts title/heat, LLM-generates chart title, CJK font detection for Chinese labels, horizontal barh with value annotations, verifies PNG output.
**Skills Used**: execute_shell_command
**Reasoning Pattern**: find JSON -> extract items -> LLM title -> generate matplotlib script -> run -> verify PNG.
**Input Format**: free-text request to chart top-N items from the workspace JSON data.
**Output Format**: returns {answer, summary}; writes trending_top20.png and plot_trending.py.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `plot_trending_bar.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "plot_trending_bar", "query": "<your focused sub-question>"}</params>
```
