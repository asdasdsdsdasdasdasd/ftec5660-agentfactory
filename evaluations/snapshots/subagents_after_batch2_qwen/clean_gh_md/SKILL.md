---
name: clean_gh_md
description: **Problem Category**: Web/GitHub research that extracts an organization's official GitHub data and writes a clean markdown report.
entry_file: clean_gh_md.py
---

# clean_gh_md

## Description
**Problem Category**: Web/GitHub research that extracts an organization's official GitHub data and writes a clean markdown report.
**Applicable Questions**: 'Find org X's GitHub page and report its description and main repositories', 'list an org's top repos from github.com', any GitHub-org metadata/repo extraction saved to markdown.
**Key Features**: LLM parses the task to resolve the GitHub org slug (from task text, URL, or web search fallback); pulls authoritative org metadata (name, description field, location, website, public_repos) and top repositories by stars from the GitHub REST API via curl written to temp files (avoids shell stdout 5000-char truncation); builds a single clean markdown doc with one title, one Description section, and one Main Repositories table using factual, non-fabricated descriptions (explicitly notes when the org has no formal bio set); shell-verifies the file has exactly one title/Description/repos section and no code fences.
**Skills Used**: google_search, execute_shell_command.
**Reasoning Pattern**: plan(slug/output/min repos) -> curl API to file -> python-compact parse -> LLM factual description -> pathlib clean overwrite -> grep verification.
**Input Format**: free-text research task naming an organization or GitHub org.
**Output Format**: returns {answer, summary}; writes a clean single-section markdown file.
**Improved From**: Replaces earlier flawed versions that (1) failed with 'Invalid control character ... char 5000' because they parsed truncated shell stdout, and (2) produced duplicated title/Description/repos sections by relying on non-verified writes. This version writes API responses to files, parses via python, and verifies the final file structurally.

## Skills Used
execute_shell_command, google_search

## Usage

**Entry file**: `clean_gh_md.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "clean_gh_md", "query": "<your focused sub-question>"}</params>
```
