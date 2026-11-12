---
name: report_writer
description: **Problem Category**: Analytical markdown report generation from free-text content/instructions.
entry_file: report_writer.py
---

# report_writer

## Description
**Problem Category**: Analytical markdown report generation from free-text content/instructions.
**Applicable Questions**: Any task ending with 'write/save a report to a markdown file' where the content is prose + numbers + tables (analysis write-ups), not just link lists.
**Key Features**: LLM assembles a complete, well-formatted markdown document faithfully preserving all supplied facts, tables, and statistics; writes the file and verifies via ls/wc. Unlike link-table-only writers, it preserves narrative structure and numbers.
**Skills Used**: execute_shell_command, call_llm.
**Reasoning Pattern**: LLM build full markdown -> write file -> shell verify -> LLM summary.
**Input Format**: Free-text report content/instructions plus desired .md filename.
**Output Format**: returns {answer, summary}; writes the specified .md filename.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `report_writer.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "report_writer", "query": "<your focused sub-question>"}</params>
```
