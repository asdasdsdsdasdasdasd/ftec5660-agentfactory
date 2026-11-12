---
name: scatter_reg
description: **Problem Category**: Scatter plot with linear regression from inline paired numeric data.
entry_file: scatter_reg.py
---

# scatter_reg

## Description
**Problem Category**: Scatter plot with linear regression from inline paired numeric data.
**Applicable Questions**: Any request to plot x-vs-y paired observations as a scatter chart and fit/overlay a regression line, with year/id labels and fit statistics.
**Key Features**: LLM extracts clean (x,y,label) pairs and chart spec from the query, writes scatter_data.json, generates a robust matplotlib script (via a newline-token template that avoids escaping bugs), computes OLS slope/intercept/R²/r with numpy, annotates the equation and stats on the chart, verifies the PNG. Runs the chart inside a 'charts' subdir to avoid stdlib module shadowing. Robust to many input formats.
**Skills Used**: execute_shell_command
**Reasoning Pattern**: check/install matplotlib+numpy -> LLM extract dataset+spec -> run matplotlib in subdir -> read fit stats -> verify output.
**Input Format**: free-text request with paired (x, y) data points plus desired title/axis labels; regression requested implicitly/explicitly.
**Output Format**: returns {answer, summary}; writes scatter_data.json, make_scatter.py, scatter_regression.png, charts/fit_stats.json.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `scatter_reg.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "scatter_reg", "query": "<your focused sub-question>"}</params>
```
