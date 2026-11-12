---
name: github_api_debugger
description: **Problem Category**: Diagnose GitHub API/network reachability in the execution environment. **Applicable Questions**: 'Is api.github.com reachable?', 'Why do GitHub API fetches return empty?', 'Which...
entry_file: github_api_debugger.py
---

# github_api_debugger

## Description
**Problem Category**: Diagnose GitHub API/network reachability in the execution environment. **Applicable Questions**: 'Is api.github.com reachable?', 'Why do GitHub API fetches return empty?', 'Which fetch method works for GitHub in this env?'. **Key Features**: Runs probes (curl with HTTP status codes, Python urllib, read_url_jina) against GitHub endpoints and uses the LLM to report which method reliably returns structured JSON. Useful for debugging empty-result failures when fetching GitHub data. **Skills Used**: execute_shell_command, read_url_jina. **Input Format**: free-text (e.g. org to probe). **Output Format**: {answer (raw probe evidence), summary}.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `github_api_debugger.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "github_api_debugger", "query": "<your focused sub-question>"}</params>
```
