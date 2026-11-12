---
name: travel_itinerary_planner
description: **Problem Category**: Constraint-satisfying multi-day travel itinerary planning with cost and travel-time budgeting.
entry_file: travel_itinerary_planner.py
---

# travel_itinerary_planner

## Description
**Problem Category**: Constraint-satisfying multi-day travel itinerary planning with cost and travel-time budgeting.
**Applicable Questions**: Any request to plan a multi-day trip itinerary under a budget, with requirements (per-day cultural attractions, required site types, total inter-location travel-time limits, etc.).
**Key Features**: LLM autonomously plans diverse web searches (cost/attraction + transit-time passes), fetches pages, extracts numeric evidence per document, then emits a COMPACT structured JSON plan (days, stops, legs, budget_items). Markdown is rendered DETERMINISTICALLY from the JSON, so total cost and total travel time are computed by summation (no truncation, no inconsistency). Renders sources, day-by-day tables, budget table, total cost, travel-time table, and a constraint-check block with automated pass/fail.
**Skills Used**: google_search (search_serper), read_url_jina
**Reasoning Pattern**: plan queries -> search+fetch (2 passes: costs & attractions, then transit times) -> per-doc evidence extraction -> single compact JSON plan -> deterministic markdown render + computed totals -> constraint verification -> consistent LLM summary.
**Input Format**: free-text trip request (destination, days, budget, and any constraints).
**Output Format**: returns {answer: full markdown itinerary, summary}; writes itinerary.md and travel_evidence.json.

## Skills Used
google_search, read_url_jina

## Usage

**Entry file**: `travel_itinerary_planner.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "travel_itinerary_planner", "query": "<your focused sub-question>"}</params>
```
