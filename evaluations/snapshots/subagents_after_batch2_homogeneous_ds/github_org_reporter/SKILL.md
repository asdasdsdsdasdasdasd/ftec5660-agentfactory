---
name: github_org_reporter
description: **Problem Category**: Fetch a GitHub organization's profile and main repositories and write a markdown report. **Applicable Questions**: 'Find <org>'s GitHub page and list its main repositories', 'Get...
entry_file: github_org_reporter.py
---

# github_org_reporter

## Description
**Problem Category**: Fetch a GitHub organization's profile and main repositories and write a markdown report. **Applicable Questions**: 'Find <org>'s GitHub page and list its main repositories', 'Get the top/starred repos of a GitHub org', 'Describe GitHub organization X and its key projects'. **Key Features**: Fully input-driven and generic (works for ANY GitHub org). LLM parses the query to identify org handle, display name, minimum repo count, and output filename. Resolves handle (API probe of org/user endpoints + web-search fallback), fetches org profile and repositories via the SEARCH API (`/search/repositories?q=org:{handle}+fork:false&sort=stars&order=desc`) with a paged org-repos client-side-sort fallback, lets the LLM select notable non-fork repos, writes a clean markdown report, and produces an LLM summary. Uses Python urllib directly (NOT execute_shell_command) to avoid the shell tool's 5000-char stdout truncation that corrupts large JSON. Handles orgs with empty raw description by synthesizing one from flagship repos. **Skills Used**: execute_shell_command, read_url_jina, google_search. **Reasoning Pattern**: parse query -> resolve handle -> fetch org profile + top-starred repos -> LLM selects -> write markdown -> summarize. **Input Format**: free-text request naming/describing a GitHub organization. **Output Format**: {answer, summary} + markdown file.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `github_org_reporter.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "github_org_reporter", "query": "<your focused sub-question>"}</params>
```
