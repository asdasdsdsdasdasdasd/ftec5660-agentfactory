import json
import re
from llm import call_llm
from tools import search_serper, read_url_jina


def _parse_json(text):
    if not text:
        return None
    t = text.strip()
    t = re.sub(r"^```(?:json)?", "", t).strip()
    t = re.sub(r"```$", "", t).strip()
    try:
        return json.loads(t)
    except Exception:
        pass
    m = re.search(r"\{.*\}", t, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


def _collect(queries, focus, max_docs=10):
    seen, candidates, log = set(), [], []
    for q in queries:
        try:
            results = search_serper(q, topk=8)
        except Exception as e:
            log.append(f"Query '{q}' failed: {e}"); continue
        if results and isinstance(results[0], dict) and "error" in results[0]:
            log.append(f"Query '{q}' error: {results[0]['error']}"); continue
        n_new = 0
        for r in results:
            link = r.get("link")
            if link and link not in seen:
                seen.add(link); candidates.append(r); n_new += 1
        log.append(f"Query '{q}' -> {len(results)} results, {n_new} new")
    docs = []
    for r in candidates[:max_docs]:
        url = r.get("link"); title = r.get("title", ""); snippet = r.get("snippet", "")
        if not url:
            continue
        try:
            content = read_url_jina(url)
        except Exception as e:
            content = {"error": str(e)}
        if isinstance(content, dict) and "error" in content:
            docs.append({"url": url, "title": title, "content": snippet}); continue
        text = content if isinstance(content, str) else content.get("text", "")
        docs.append({"url": url, "title": title, "content": (text or "")[:6000]})
    evidence = []
    for d in docs:
        if not d.get("content"):
            continue
        per = call_llm(
            system=(
                "You extract evidence from ONE web document for itinerary planning. "
                "Return ONLY JSON: {'relevant': bool, 'evidence': [ {'text': short passage with a concrete number/fact} , ... up to 5 ]}. "
                "Capture concrete numeric data: admission fees, transport fares, travel minutes between locations, meal prices, opening hours. Keep each text <=30 words. No markdown."
            ),
            messages=[{"role": "user", "content": f"Focus: {focus}\n\nDoc title: {d['title']}\nURL: {d['url']}\n\nContent:\n{d['content'][:5000]}"}],
            max_tokens=1000,
        )
        parsed = _parse_json(per)
        if parsed and isinstance(parsed, dict):
            for ev in (parsed.get("evidence") or []):
                if isinstance(ev, dict) and ev.get("text"):
                    evidence.append({"text": str(ev["text"])[:400], "source": d["url"], "title": d["title"]})
    return docs, evidence, log


def _extract_budget(query):
    m = re.search(r'\$\s*([0-9][0-9,]*(?:\.[0-9]+)?)', query)
    if m:
        try:
            return float(m.group(1).replace(',', ''))
        except Exception:
            return None
    return None


def _extract_travel_limit(query):
    ql = query.lower()
    m = re.search(r'under\s+([0-9]+(?:\.[0-9]+)?)\s*(hour|hr|h)', ql)
    if m:
        try:
            return float(m.group(1)) * 60.0
        except Exception:
            return None
    m = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*(hour|hr|h)\b', ql)
    if m:
        try:
            return float(m.group(1)) * 60.0
        except Exception:
            return None
    return None


def _build_queries(query):
    plan = call_llm(
        system=("You are a travel research planner. Given a trip-planning request, produce JSON with 'queries' (5-7 diverse web search queries) to surface: itinerary ideas, admission fees of typical/named attractions, public-transport travel times & fares between areas, and budget food costs for the destination. Also 'focus'. Return ONLY JSON."),
        messages=[{"role": "user", "content": f"Trip request: {query}"}], max_tokens=900,
    )
    parsed = _parse_json(plan)
    if parsed and parsed.get("queries"):
        return parsed["queries"], parsed.get("focus", query)
    return [query], query


def _build_queries_travel(query):
    plan = call_llm(
        system=("You are a transit research planner. Produce JSON with 'queries' (3-5 web search queries) focused on public-transport travel TIMES (minutes) and FARES between the candidate locations/areas in the trip so transit can be summed. Also 'focus'. Return ONLY JSON."),
        messages=[{"role": "user", "content": f"Trip request: {query}"}], max_tokens=700,
    )
    parsed = _parse_json(plan)
    if parsed and parsed.get("queries"):
        return parsed["queries"], parsed.get("focus", "travel times and fares")
    return [query + " travel times between locations subway fares minutes"], "travel times and fares"


def main(query: str) -> dict:
    all_ev, all_docs, all_log = [], [], []
    q1, f1 = _build_queries(query)
    d1, e1, l1 = _collect(q1, f1, max_docs=10); all_ev += e1; all_docs += d1; all_log += l1
    q2, f2 = _build_queries_travel(query)
    d2, e2, l2 = _collect(q2, f2, max_docs=6); all_ev += e2; all_docs += d2; all_log += l2

    seen, dedup = set(), []
    for e in all_ev:
        k = e["text"][:100]
        if k not in seen:
            seen.add(k); dedup.append(e)
    ev_text = "\n".join(f"- [{e['source']}] {e['text']}" for e in dedup[:70])

    struct = call_llm(
        system=(
            "You are an expert budget travel planner and accountant. Build a FINAL trip plan as ONE compact JSON object. Do NOT write any prose or reasoning outside the JSON. "
            "Schema: {'exchange_rate': str, 'budget_cap_usd': number, 'travel_limit_min': number, 'days': [ {'day': int, 'theme': str, 'cultural_attraction': str, 'anime_location': str_or_empty, 'stops': [ {'time': str, 'name': str, 'type': str, 'cost_usd': number, 'notes': str} ] } ], "
            "'legs': [ {'day': int, 'from': str, 'to': str, 'mode': str, 'minutes': number} ], "
            "'budget_items': [ {'category': str, 'item': str, 'cost_usd': number, 'basis': str} ], 'sources': [str]}. "
            "Rules: satisfy EVERY constraint in the request (a cultural attraction per day, any required site types, travel-time limit, budget cap). Use a geographically sensible route minimizing backtracking. "
            "Include ALL inter-location legs for ALL days with minute values. Give every cost as a USD number. If evidence missing a value, use a realistic well-known estimate and note 'estimate'. "
            "CRITICAL: the 'basis' field must be <=12 words, a clean factual note (e.g. '1500 JPY 72h pass' or 'estimate'). Do NOT include any deliberation, 'wait', or re-evaluation text anywhere. Return ONLY the JSON."
        ),
        messages=[{"role": "user", "content": f"Trip request:\n{query}\n\nCollected evidence:\n{ev_text}\n\nReturn the JSON plan now."}],
        max_tokens=4000,
    )
    plan = _parse_json(struct) or {}
    days = plan.get("days", []) or []
    legs = plan.get("legs", []) or []
    budget_items = plan.get("budget_items", []) or []
    sources = plan.get("sources", []) or []
    total_travel_min = sum(int(l.get("minutes", 0) or 0) for l in legs)
    total_cost = round(sum(float(b.get("cost_usd", 0) or 0) for b in budget_items), 2)
    days_with_culture = sum(1 for d in days if d.get("cultural_attraction"))
    has_anime = any(d.get("anime_location") for d in days)

    md = ["# Budget Trip Itinerary", ""]
    if plan.get("exchange_rate"):
        md += [f"**Exchange rate used:** {plan['exchange_rate']}", ""]
    md.append("## Shortlist of Sources")
    for s in sources[:12]:
        md.append(f"- {s}")
    md += ["", "## Day-by-Day Itinerary"]
    for d in days:
        md.append(f"### Day {d.get('day','?')}: {d.get('theme','')}")
        md.append(f"*Cultural attraction:* {d.get('cultural_attraction','')}")
        if d.get("anime_location"):
            md.append(f"*Anime-related location:* {d['anime_location']}")
        md += ["", "| Time | Stop | Type | Cost USD | Notes |", "| --- | --- | --- | --- | --- |"]
        for st in d.get("stops", []):
            md.append(f"| {st.get('time','')} | {st.get('name','')} | {st.get('type','')} | {st.get('cost_usd','')} | {st.get('notes','')} |")
        md.append("")
    md += ["## Budget Breakdown", "| Category | Item | Cost USD | Basis |", "| --- | --- | --- | --- |"]
    for b in budget_items:
        md.append(f"| {b.get('category','')} | {b.get('item','')} | {b.get('cost_usd','')} | {b.get('basis','')} |")
    md.append(f"| **TOTAL** | | **${total_cost:.2f}** | |")
    md += ["", "## Total Cost", f"**${total_cost:.2f} USD**", ""]
    md += ["## Total Travel Time", "| Day | From | To | Mode | Minutes |", "| --- | --- | --- | --- | --- |"]
    for l in legs:
        md.append(f"| {l.get('day','')} | {l.get('from','')} | {l.get('to','')} | {l.get('mode','')} | {l.get('minutes','')} |")
    md.append("")
    md.append(f"**Total inter-location travel time: {total_travel_min} minutes ({total_travel_min/60:.2f} hours).**")
    result = "\n".join(md)

    budget_cap = plan.get('budget_cap_usd') or _extract_budget(query)
    travel_limit_min = plan.get('travel_limit_min') or _extract_travel_limit(query)
    within_budget = total_cost <= (float(budget_cap) if budget_cap else 1e9)
    within_travel = total_travel_min < (float(travel_limit_min) if travel_limit_min else 1e9)
    ver = {
        "all_constraints_met": bool(within_budget and within_travel and days_with_culture >= len(days)),
        "budget_cap_usd": budget_cap, "budget_total_usd": total_cost, "within_budget": within_budget,
        "travel_limit_min": travel_limit_min, "total_travel_time_hours": round(total_travel_min / 60.0, 2), "within_travel_limit": within_travel,
        "days_with_culture": days_with_culture, "has_anime": has_anime, "num_days": len(days), "num_legs": len(legs),
    }
    checklist = []
    checklist.append("## Constraint Check")
    _cap = ver.get('budget_cap_usd'); _tlim = ver.get('travel_limit_min')
    checklist.append(f"- Total cost: ${total_cost:.2f} (budget cap = {('$'+format(float(_cap),'.2f')) if _cap else 'n/a'}; within budget = {ver['within_budget']})")
    checklist.append(f"- Total travel time: {total_travel_min} min = {total_travel_min/60:.2f} h (limit = {(_tlim/60.0) if _tlim else 'n/a'} h; within limit = {ver['within_travel_limit']})")
    checklist.append(f"- Days with cultural attraction (museum): {days_with_culture} of {len(days)}")
    checklist.append(f"- Historic landmark present: {any('landmark' in str(d.get('cultural_attraction','')).lower() or any('landmark' in str(s.get('type','')).lower() for s in d.get('stops',[])) for d in days)}")
    result = result + "\n" + "\n".join(checklist)
    plan_doc = result + "\n\n---\n### Verification (automated)\n" + json.dumps(ver, indent=2)
    try:
        with open("itinerary.md", "w") as f:
            f.write(plan_doc)
        with open("travel_evidence.json", "w") as f:
            json.dump({"evidence": dedup, "documents": [{"url": d["url"], "title": d["title"]} for d in all_docs], "log": all_log}, f, indent=2, ensure_ascii=False)
    except Exception as e:
        all_log.append(f"save error: {e}")

    summary = call_llm(
        system="You are a research summarizer. Write a detailed SUMMARY (150-1200 words) that MUST be consistent with the final plan text provided. Trace the searches run, documents fetched, key numeric evidence (fees/minutes/prices), and the computed totals verified against constraints. Describe the SAME itinerary that appears in the plan.",
        messages=[{"role": "user", "content": f"Request: {query}\n\nFINAL PLAN (authoritative):\n{result}\n\nSearch log:\n" + "\n".join(all_log) + f"\n\nDocuments: {len(all_docs)}\nEvidence: {len(dedup)}\nVerification: {json.dumps(ver)}\n\nWrite the SUMMARY consistent with the FINAL PLAN above."}],
        max_tokens=2500,
    )
    return {"answer": plan_doc, "summary": summary}
