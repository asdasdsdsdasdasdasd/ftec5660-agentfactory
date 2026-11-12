---
name: json_timeseries_plotter
description: **Problem Category**: Visualization of pre-collected numeric time-series data stored in JSON files.
entry_file: json_timeseries_plotter.py
---

# json_timeseries_plotter

## Description
**Problem Category**: Visualization of pre-collected numeric time-series data stored in JSON files.
**Applicable Questions**: Any task requiring a matplotlib chart (line/bar) from a JSON time-series file shaped as {series:[{name,unit,values:{year:value}}]} — e.g., plotting population, GDP, or any year-by-value series produced by a prior data-fetching step.
**Key Features**: LLM selects the best JSON file from the workspace, loads and normalizes year->value points, LLM generates a chart spec (title, axis labels, chart type, linear/log scale, scale_factor for unit conversion like millions), writes a standalone matplotlib script, runs it, and verifies the output PNG exists.
**Skills Used**: execute_shell_command
**Reasoning Pattern**: list JSON files -> LLM picks file -> load series -> LLM chart spec -> generate & run matplotlib script -> verify PNG.
**Input Format**: free-text plotting request (what to plot, desired axes/units/title).
**Output Format**: returns {answer, summary}; writes plot_payload.json, make_chart.py, and population_chart.png.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `json_timeseries_plotter.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "json_timeseries_plotter", "query": "<your focused sub-question>"}</params>
```
