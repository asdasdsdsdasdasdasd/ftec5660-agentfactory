---
name: check_md
description: **Problem Category**: Verify and display the contents of a generated markdown/txt output file. **Applicable Questions**: 'Did the report file get written?', 'Show the contents of output.md'. **Key Fea...
entry_file: check_md.py
---

# check_md

## Description
**Problem Category**: Verify and display the contents of a generated markdown/txt output file. **Applicable Questions**: 'Did the report file get written?', 'Show the contents of output.md'. **Key Features**: Lists matching .md files and prints their content for verification; LLM summarizes what the file contains. **Skills Used**: execute_shell_command. **Input Format**: free-text (which file to check). **Output Format**: {answer (file listing + content), summary}.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `check_md.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "check_md", "query": "<your focused sub-question>"}</params>
```
