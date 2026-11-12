---
name: file_scatter
description: **Problem Category**: Scatter plot + OLS regression read from a JSON file of paired records.
entry_file: file_scatter.py
---

# file_scatter

## Description
**Problem Category**: Scatter plot + OLS regression read from a JSON file of paired records.
**Applicable Questions**: Any request to plot x-vs-y from an on-disk JSON dataset (rows with columns) and fit/annotate a linear regression line with fit statistics.
**Key Features**: LLM reads column names and decides x/y mapping, optional derived axis via a python expression (e.g. pct/100*gdp), scale, and labels/title; computes OLS slope/intercept/R²/r with numpy; annotates equation, stats, and well-sized chart; verifies PNG output.
**Skills Used**: execute_shell_command
**Reasoning Pattern**: locate JSON -> LLM derive plot spec (columns + optional derivation) -> build points -> generate matplotlib script -> run -> verify PNG -> summarize fit.
**Input Format**: free-text request referencing a .json file plus desired x/y variables and any derivation.
**Output Format**: returns {answer, summary}; writes plot_input.json, make_scatter_file.py, scatter_regression.png.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `file_scatter.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "file_scatter", "query": "<your focused sub-question>"}</params>
```
