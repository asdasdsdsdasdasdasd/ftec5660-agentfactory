---
name: data_plotter
description: **Problem Category**: LLM-driven data visualization / charting from inline numeric data.
entry_file: data_plotter.py
---

# data_plotter

## Description
**Problem Category**: LLM-driven data visualization / charting from inline numeric data.
**Applicable Questions**: Any request to plot numeric data over time or an ordered dimension into a matplotlib chart (line/bar/scatter).
**Key Features**: LLM extracts a clean dataset and chart spec (title, axis labels, chart type) from the query at runtime, normalizes numeric x/y, writes plot_data.json, generates and runs a standalone matplotlib script with a fallback, and verifies the PNG exists.
**Skills Used**: execute_shell_command
**Reasoning Pattern**: check/install matplotlib -> LLM extract dataset+spec -> normalize points -> generate script -> run -> fallback -> verify output.
**Input Format**: free-text request containing the numeric data points to visualize plus desired chart title/axes/type.
**Output Format**: returns {answer, summary}; writes plot_data.json, make_chart.py, and population_chart.png.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `data_plotter.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "data_plotter", "query": "<your focused sub-question>"}</params>
```
