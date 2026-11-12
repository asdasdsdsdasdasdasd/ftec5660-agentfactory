---
name: web_meeting_booker
description: **Problem Category**: Web meeting/event booking via browser automation.
entry_file: web_meeting_booker.py
---

# web_meeting_booker

## Description
**Problem Category**: Web meeting/event booking via browser automation.
**Applicable Questions**: Any task to book/create a meeting or scheduled event on a web application through UI automation (Tencent Meeting, Zoom, calendar schedulers, etc.).
**Key Features**: LLM-driven Playwright loop that derives a start URL via web search, then iteratively discovers the booking entry, fills topic/date/time, and confirms creation; handles iframes, popups, native selects, and detects login-redirect blockers. Extracts meeting ID/link from confirmation page.
**Skills Used**: playwright, google_search
**Reasoning Pattern**: search for entry URL -> navigate -> think/act/observe loop -> confirm -> extract details
**Input Format**: free-text booking request (topic, date, time, app).
**Output Format**: returns {answer, summary} with meeting invitation/ID/link or blocker report.

## Skills Used
playwright

## Usage

**Entry file**: `web_meeting_booker.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "web_meeting_booker", "query": "<your focused sub-question>"}</params>
```
