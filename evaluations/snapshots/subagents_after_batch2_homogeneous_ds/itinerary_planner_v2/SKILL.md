---
name: itinerary_planner_v2
description: **Problem Category**: Constraint-satisfying multi-day travel itinerary planning with cost and travel-time budgeting.
entry_file: itinerary_planner_v2.py
---

# itinerary_planner_v2

## Supersedes
This skill replaces `travel_itinerary_planner`. See description for what was improved.

## Description
**Problem Category**: Constraint-satisfying multi-day travel itinerary planning with cost and travel-time budgeting.
**Applicable Questions**: Any request to plan a multi-day trip itinerary under a budget, with per-day/per-trip requirement constraints (e.g. at least one museum per day, at least one historic landmark, total inter-location travel-time limit), and to output daily itinerary, budget breakdown, total cost, and total travel time.
**Key Features**: Parses ALL constraints dynamically from the free-text query via LLM (destination, days, budget cap, max total travel minutes, per-day required attraction types, total-only required types) — nothing hardcoded. Two passes of search+fetch (costs/attractions, then transit times), per-document numeric evidence extraction, single compact JSON plan, then DETERMINISTIC markdown render with summed totals and an automated PASS/FAIL constraint-check block.
**Skills Used**: google_search, read_url_jina
**Reasoning Pattern**: LLM constraint-parsing -> query planning -> search+fetch (2 passes) -> per-doc evidence extraction -> compact JSON plan -> deterministic markdown + computed totals -> automated constraint verification -> consistent LLM summary.
**Input Format**: free-text trip request (destination, days, budget, and any per-day/total requirement constraints and travel-time limits).
**Output Format**: returns {answer: full markdown itinerary, summary}; writes itinerary.md and travel_evidence.json.
**Improved From**: the older `travel_itinerary_planner`, which hardcoded a $100 budget cap, a 5-hour travel limit, and an 'anime location' requirement, and lacked dynamic museum-per-day / historic-landmark checks. This version reads all limits and requirement types from the query at runtime, verifies per-day and total-only requirements generically, and reports each constraint as PASS/FAIL.

## Skills Used
google_search, read_url_jina

## Usage

**Entry file**: `itinerary_planner_v2.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "itinerary_planner_v2", "query": "<your focused sub-question>"}</params>
```
