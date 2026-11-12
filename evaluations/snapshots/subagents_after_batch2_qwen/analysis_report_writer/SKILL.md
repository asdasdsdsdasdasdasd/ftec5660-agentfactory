---
name: analysis_report_writer
description: **Problem Category**: Structured Markdown report generation from analysis output files.
entry_file: analysis_report_writer.py
---

# analysis_report_writer

## Description
**Problem Category**: Structured Markdown report generation from analysis output files.
**Applicable Questions**: Any task requiring a written report summarizing data analysis results and referenced plots.
**Key Features**: collects analysis_results.json and fetched_data.json summaries; LLM writes a structured report with source, methodology, quantitative findings, interpretation, limitations, conclusion; writes analysis_report.md.
**Skills Used**: execute_shell_command
**Reasoning Pattern**: gather evidence files -> LLM write markdown report -> save file -> LLM summary.
**Input Format**: free-text task describing the report to write.
**Output Format**: {answer, summary}; writes analysis_report.md.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `analysis_report_writer.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "analysis_report_writer", "query": "<your focused sub-question>"}</params>
```
