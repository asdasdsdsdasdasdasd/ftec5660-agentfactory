---
name: timeseries_correlation_analyzer
description: **Problem Category**: Correlation and trend analysis between two numeric metrics in tidy-row JSON data.
entry_file: timeseries_correlation_analyzer.py
---

# timeseries_correlation_analyzer

## Description
**Problem Category**: Correlation and trend analysis between two numeric metrics in tidy-row JSON data.
**Applicable Questions**: Any request to correlate/analyze trends between two variables across entities over time and visualize them.
**Key Features**: LLM extracts config (file, entity key, time key, metric columns, labels, title); computes pooled Pearson r, OLS slope/R², per-entity within-group correlations and % changes; generates a two-panel trends plot and a labeled correlation scatter with regression line.
**Skills Used**: execute_shell_command
**Reasoning Pattern**: parse config (LLM) -> pandas groupby/corr/np.polyfit -> write analysis_results.json -> matplotlib plots -> LLM insight summary.
**Input Format**: free-text query naming the input JSON and the two metrics.
**Output Format**: {answer, summary}; writes analysis_results.json, trends_plot.png, correlation_scatter.png.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `timeseries_correlation_analyzer.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "timeseries_correlation_analyzer", "query": "<your focused sub-question>"}</params>
```
