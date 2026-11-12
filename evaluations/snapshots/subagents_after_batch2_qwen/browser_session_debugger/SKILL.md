---
name: browser_session_debugger
description: **Problem Category**: Browser login/session verification diagnostics.
entry_file: browser_session_debugger.py
---

# browser_session_debugger

## Description
**Problem Category**: Browser login/session verification diagnostics.
**Applicable Questions**: Determining whether a web application is authenticated in any Playwright browser profile before attempting automation; debugging 'redirected to login' failures.
**Key Features**: Discovers all .browser_profile directories, launches each, navigates to a target site, and reports final URL, cookie inventory (with domain filtering), and landing-page text to determine login state.
**Skills Used**: playwright
**Reasoning Pattern**: discover profiles -> launch each -> navigate -> collect url/cookies/text -> LLM verdict
**Input Format**: free-text diagnostic request naming the target site.
**Output Format**: returns {answer (per-profile JSON), summary} with authentication verdict.

## Skills Used
playwright

## Usage

**Entry file**: `browser_session_debugger.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "browser_session_debugger", "query": "<your focused sub-question>"}</params>
```
