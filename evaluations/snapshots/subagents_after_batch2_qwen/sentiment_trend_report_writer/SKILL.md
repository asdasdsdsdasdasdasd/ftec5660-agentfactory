---
name: sentiment_trend_report_writer
description: **Problem Category**: Structured Markdown analysis report generation for sentiment/trend research tasks.
entry_file: sentiment_trend_report_writer.py
---

# sentiment_trend_report_writer

## Description
**Problem Category**: Structured Markdown analysis report generation for sentiment/trend research tasks.
**Applicable Questions**: Any task requiring a written analysis report that synthesizes evidence and time-series data into a report with Discussion and Summary sections, referencing a trend chart.
**Key Features**: Auto-discovers all JSON evidence/data files and PNG charts in the workspace, loads their content, identifies the primary chart image, and has the LLM write a 900-1500 word structured report (Title, Executive Summary, Introduction, Data & Methodology, Findings, Discussion, Limitations, Summary) that embeds the chart and stays strictly grounded in provided evidence.
**Skills Used**: execute_shell_command
**Reasoning Pattern**: discover files -> load JSON/PNG context -> LLM writes full markdown report -> strip code fences -> write ev_sentiment_analysis_report.md -> LLM review summary.
**Input Format**: free-text task describing the report to write.
**Output Format**: {answer, summary}; writes ev_sentiment_analysis_report.md referencing the discovered chart PNG.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `sentiment_trend_report_writer.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "sentiment_trend_report_writer", "query": "<your focused sub-question>"}</params>
```
