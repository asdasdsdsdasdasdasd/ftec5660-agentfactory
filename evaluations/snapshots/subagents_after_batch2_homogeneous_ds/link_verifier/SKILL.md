---
name: link_verifier
description: **Problem Category**: Verify that a set of URLs are reachable by checking HTTP status codes.
entry_file: link_verifier.py
---

# link_verifier

## Description
**Problem Category**: Verify that a set of URLs are reachable by checking HTTP status codes.
**Applicable Questions**: any task needing to validate links before trusting them.
**Key Features**: Extracts all URLs from the query, runs curl -w http_code -L per URL via shell, reports status per link, LLM summarizes reachability.
**Skills Used**: execute_shell_command
**Reasoning Pattern**: extract URLs -> curl each -> collect status codes -> LLM summary.
**Input Format**: free-text query containing one or more URLs.
**Output Format**: {answer (per-url status lines), summary}.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `link_verifier.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "link_verifier", "query": "<your focused sub-question>"}</params>
```
