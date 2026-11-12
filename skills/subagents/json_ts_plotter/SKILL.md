---
name: json_ts_plotter
description: **Problem Category**: Plotting a numeric year->value time series stored in a JSON file into a matplotlib chart.
entry_file: json_ts_plotter.py
---

# json_ts_plotter

## Description
**Problem Category**: Plotting a numeric year->value time series stored in a JSON file into a matplotlib chart.
**Applicable Questions**: Any request to visualize historical/annual data (population, GDP, prices, etc.) already saved in a workspace JSON file like series_data.json or ts_fetcher output.
**Key Features**: LLM picks the JSON file and chart spec (title, axis labels, chart_type) from the query; recursively locates the largest year->value mapping in nested JSON; sorts by year, annotates the peak, and renders line/bar/scatter to population_chart.png; verifies the PNG exists and reports size and peak year.
**Skills Used**: execute_shell_command
**Reasoning Pattern**: check/install matplotlib -> LLM parse file+spec -> recursively extract year->value series -> write plot_data.json -> generate and run matplotlit script -> verify PNG.
**Input Format**: free-text request naming the JSON file (or letting it auto-detect) plus desired title/axes/chart type.
**Output Format**: returns {answer, summary}; writes plot_data.json, make_chart.py, and population_chart.png.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `json_ts_plotter.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "json_ts_plotter", "query": "<your focused sub-question>"}</params>
```
