---
name: github_sort_debugger
description: **Problem Category**: Diagnose why a GitHub org repository listing returns wrong/unexpected ordering (e.g. missing flagship repos). **Applicable Questions**: 'Why aren't the top-starred repos listed?'...
entry_file: github_sort_debugger.py
---

# github_sort_debugger

## Description
**Problem Category**: Diagnose why a GitHub org repository listing returns wrong/unexpected ordering (e.g. missing flagship repos). **Applicable Questions**: 'Why aren't the top-starred repos listed?', 'Does the GitHub API honor sort=stars?'. **Key Features**: Compares default order, `?sort=stars` (which sorts ASCENDING and returns LOW-star repos), the Search API (`/search/repositories?q=org:{org}&sort=stars&order=desc`, the reliable descending method), and client-side sort of all paged repos. Confirms the Search API as the single reliable way to get an org's top-starred repos. **Skills Used**: execute_shell_command. **Input Format**: free-text (org handle). **Output Format**: {answer (comparison evidence), summary}.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `github_sort_debugger.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "github_sort_debugger", "query": "<your focused sub-question>"}</params>
```
