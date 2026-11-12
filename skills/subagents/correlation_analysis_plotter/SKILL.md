---
name: correlation_analysis_plotter
description: **Problem Category**: Correlation analysis between two numeric variables in a tidy JSON dataset, producing a regression plot and written interpretation.
entry_file: correlation_analysis_plotter.py
---

# correlation_analysis_plotter

## Description
**Problem Category**: Correlation analysis between two numeric variables in a tidy JSON dataset, producing a regression plot and written interpretation.
**Applicable Questions**: Any request to correlate economic/social/health variables (e.g., GDP vs life expectancy, income vs outcomes) from a records-JSON file and visualize the relationship.
**Key Features**: LLM selects data file + x/y fields (with robust exact/substring/fuzzy key resolution); computes BOTH linear (raw) and log10-x (Preston-style) OLS fits with R² and r; generates a log-scale matplotlib scatter with fit line and stats box; LLM writes a rigorous interpretation (diminishing returns, outliers, causality caveats); outputs a markdown report.
**Skills Used**: execute_shell_command
**Reasoning Pattern**: list JSON -> LLM plan (file/fields/log_x) -> resolve keys -> compute dual fits -> plot -> LLM interpretation -> markdown report.
**Input Format**: free-text request naming the JSON file, x variable, y variable, and optional log-transform/title.
**Output Format**: {answer, summary}; writes correlation_scatter.png, corr_stats.json, findings_report.md, corr_bundle.json.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `correlation_analysis_plotter.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "correlation_analysis_plotter", "query": "<your focused sub-question>"}</params>
```
