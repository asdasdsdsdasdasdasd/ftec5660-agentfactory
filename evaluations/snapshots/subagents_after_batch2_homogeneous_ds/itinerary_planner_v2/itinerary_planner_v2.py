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


def _extract_constraints(query):
    raw = call_llm(
        system=(
            "You parse a trip-planning request into a constraints JSON. Return ONLY JSON with keys: "
            "'destination' (str), 'days' (int), 'budget_usd' (number or null), "
            "'max_total_travel_minutes' (number or null; convert hours to minutes, e.g. 6 hours -> 360), "
            "'required_per_day' (list of requirement strings that must appear EACH day, e.g. 'museum'), "
            "'required_total' (list of requirements that must appear at least once across the whole trip, e.g. 'historic landmark'), "
            "'other_notes' (str). If a numeric limit is absent use null. Do not invent values."
        ),
        messages=[{"role": "user", "content": f"Trip request:\n{query}"}],
        max_tokens=800,
    )
    parsed = _parse_json(raw) or {}
    return parsed


def _collect(queries, focus, max_docs=10):
    seen, candidates, log = set(), [], []
    for q in queries:
        try:
            results = search_serper(q, topk=8)
        except Exception as e:
            log.append(f"Query '{q}' failed: {e}")
            continue
        if results and isinstance(results[0], dict) and "error" in results[0]:
            log.append(f"Query '{q}' error: {results[0]['error']}")
            continue
        n_new = 0
        for r in results:
            link = r.get("link")
            if link and link not in seen:
                seen.add(link)
                candidates.append(r)
                n_new += 1
        log.append(f"Query '{q}' -> {len(results)} results, {n_new} new")
    docs = []
    for r in candidates[:max_docs]:
        url = r.get("link")
        title = r.get("title", "")
        snippet = r.get("snippet", "")
        if not url:
            continue
        try:
            content = read_url_jina(url)
        except Exception as e:
            content = {"error": str(e)}
        if isinstance(content, dict) and "error" in content:
            docs.append({"url": url, "title": title, "content": snippet})
            continue
        text = content if isinstance(content, str) else content.get("text", "")
        docs.append({"url": url, "title": title, "content": (text or "")[:6000]})
    evidence = []
    for d in docs:
        if not d.get("content"):
            continue
        per = call_llm(
            system=(
                "You extract evidence from ONE web document for itinerary planning. "
                "Return ONLY JSON: {'relevant': bool, 'evidence': [ {'text': short passage with a concrete number/fact}, ... up to 5 ]}. "
                "Capture concrete numeric data: admission fees, transport fares, travel minutes between locations, meal prices, opening hours, attraction types (museum/landmark). Keep each text <=30 words. No markdown."
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


def _build_queries(constraints):
    plan = call_llm(
        system=(
            "You are a travel research planner. Given trip constraints, produce JSON with 'queries' (5-7 diverse web search queries) to surface: "
            "itinerary ideas, admission fees of typical/named attractions (museums, landmarks), public-transport travel times & fares between areas, and budget food costs. "
            "Also 'focus'. Return ONLY JSON."
        ),
        messages=[{"role": "user", "content": f"Constraints: {json.dumps(constraints)}"}],
        max_tokens=900,
    )
    parsed = _parse_json(plan)
    if parsed and parsed.get("queries"):
        return parsed["queries"], parsed.get("focus", "costs and attractions")
    return [f"{constraints.get('destination','')} budget travel costs attractions"], "costs and attractions"


def _build_queries_travel(constraints):
    plan = call_llm(
        system=(
            "You are a transit research planner. Produce JSON with 'queries' (3-5 web search queries) focused on public-transport travel TIMES (minutes) and FARES between the candidate locations/areas in the trip so transit can be summed. Also 'focus'. Return ONLY JSON."
        ),
        messages=[{"role": "user", "content": f"Constraints: {json.dumps(constraints)}"}],
        max_tokens=700,
    )
    parsed = _parse_json(plan)
    if parsed and parsed.get("queries"):
        return parsed["queries"], parsed.get("focus", "travel times and fares")
    return [f"{constraints.get('destination','')} travel times between attractions subway fares minutes"], "travel times and fares"


def main(query: str) -> dict:
    constraints = _extract_constraints(query)
    dest = constraints.get("destination", "")
    n_days = constraints.get("days") or 3
    budget = constraints.get("budget_usd")
    travel_limit = constraints.get("max_total_travel_minutes")
    required_per_day = constraints.get("required_per_day") or []
    required_total = constraints.get("required_total") or []

    all_ev, all_docs, all_log = [], [], []
    q1, f1 = _build_queries(constraints)
    d1, e1, l1 = _collect(q1, f1, max_docs=10)
    all_ev += e1; all_docs += d1; all_log += l1
    q2, f2 = _build_queries_travel(constraints)
    d2, e2, l2 = _collect(q2, f2, max_docs=6)
    all_ev += e2; all_docs += d2; all_log += l2

    seen, dedup = set(), []
    for e in all_ev:
        k = e["text"][:100]
        if k not in seen:
            seen.add(k); dedup.append(e)
    ev_text = "\n".join(f"- [{e['source']}] {e['text']}" for e in dedup[:70])

    req_desc = (
        f"For EACH of the {n_days} days include at least: {required_per_day if required_per_day else 'no specific per-day type'}. "
        f"Across the whole trip include at least once: {required_total if required_total else 'no specific total-only type'}."
    )
    struct = call_llm(
        system=(
            "You are an expert budget travel planner and accountant. Build a FINAL trip plan as ONE compact JSON object. Do NOT write any prose outside the JSON. "
            "Schema: {'exchange_rate': str, 'days': [ {'day': int, 'theme': str, 'stops': [ {'time': str, 'name': str, 'type': str, 'cost_usd': number, 'notes': str} ] } ], "
            "'legs': [ {'day': int, 'from': str, 'to': str, 'mode': str, 'minutes': number} ], "
            "'budget_items': [ {'category': str, 'item': str, 'cost_usd': number, 'basis': str} ], 'sources': [str]}. "
            "Rules: satisfy EVERY constraint given (per-day required attraction types, total-only required types, travel-time limit, budget cap). Use a geographically sensible route minimizing backtracking. "
            "The 'type' field of each stop must explicitly label museum/landmark/park/cafe/meal/transport etc. Include ALL inter-location legs for ALL days with minute values. "
            "Give every cost as a USD number (convert from local currency if needed and record exchange_rate). If evidence missing a value, use a realistic well-known estimate and note 'estimate'. "
            "Be economical to stay under budget. The 'basis' field must be <=12 words, clean factual. Return ONLY the JSON."
        ),
        messages=[{"role": "user", "content": (
            f"Trip request:\n{query}\n\nDestination: {dest}; Days: {n_days}; Budget USD: {budget}; \n"
            f"Max total inter-location travel minutes: {travel_limit}.\n{req_desc}\n\n"
            f"Collected evidence:\n{ev_text}\n\nReturn the JSON plan now."
        )}],
        max_tokens=4000,
    )
    plan = _parse_json(struct) or {}
    days = plan.get("days", []) or []
    legs = plan.get("legs", []) or []
    budget_items = plan.get("budget_items", []) or []
    sources = plan.get("sources", []) or []
    total_travel_min = sum(int(l.get("minutes", 0) or 0) for l in legs)
    total_cost = round(sum(float(b.get("cost_usd", 0) or 0) for b in budget_items), 2)

    def day_has(day, keyword):
        kw = keyword.lower().strip()
        for st in day.get("stops", []):
            blob = (str(st.get("type","")) + " " + str(st.get("name","")) + " " + str(st.get("notes",""))).lower()
            if kw in blob:
                return True
        return False

    per_day_ok = True
    per_day_detail = []
    for d in days:
        missing = [r for r in required_per_day if not day_has(d, r)]
        ok = len(missing) == 0
        per_day_ok = per_day_ok and ok
        per_day_detail.append((d.get("day"), ok, missing))

    total_ok = True
    total_detail = []
    for r in required_total:
        found = any(day_has(d, r) for d in days)
        total_ok = total_ok and found
        total_detail.append((r, found))

    budget_ok = (budget is None) or (total_cost <= float(budget))
    travel_ok = (travel_limit is None) or (total_travel_min <= float(travel_limit))
    num_days_ok = len(days) == n_days

    md = [f"# Budget Trip Itinerary: {dest}", ""]
    if plan.get("exchange_rate"):
        md += [f"**Exchange rate used:** {plan['exchange_rate']}", ""]
    md.append("## Sources")
    for s in sources[:12]:
        md.append(f"- {s}")
    md += ["", "## Day-by-Day Itinerary"]
    for d in days:
        md.append(f"### Day {d.get('day','?')}: {d.get('theme','')}")
        md += ["", "| Time | Stop | Type | Cost USD | Notes |", "| --- | --- | --- | --- | --- |"]
        for st in d.get("stops", []):
            md.append(f"| {st.get('time','')} | {st.get('name','')} | {st.get('type','')} | {st.get('cost_usd','')} | {st.get('notes','')} |")
        md.append("")
    md += ["## Budget Breakdown", "| Category | Item | Cost USD | Basis |", "| --- | --- | --- | --- |"]
    for b in budget_items:
        md.append(f"| {b.get('category','')} | {b.get('item','')} | {b.get('cost_usd','')} | {b.get('basis','')} |")
    md.append(f"| **TOTAL** | | **${total_cost:.2f}** | |")
    md += ["", "## Total Cost", f"**${total_cost:.2f} USD**" + (f" (budget ${float(budget):.0f} USD)" if budget is not None else ""), ""]
    md += ["## Total Travel Time", "| Day | From | To | Mode | Minutes |", "| --- | --- | --- | --- | --- |"]
    for l in legs:
        md.append(f"| {l.get('day','')} | {l.get('from','')} | {l.get('to','')} | {l.get('mode','')} | {l.get('minutes','')} |")
    md.append("")
    md.append(f"**Total inter-location travel time: {total_travel_min} minutes ({total_travel_min/60:.2f} hours).**")
    md += ["", "## Constraint Check"]
    md.append(f"- Total cost: ${total_cost:.2f}" + (f" within budget ${float(budget):.0f} = {'PASS' if budget_ok else 'FAIL'}" if budget is not None else " (no budget constraint)"))
    md.append(f"- Total travel time: {total_travel_min} min = {total_travel_min/60:.2f} h" + (f" under {float(travel_limit)/60:.2f} h = {'PASS' if travel_ok else 'FAIL'}" if travel_limit is not None else " (no travel limit)"))
    md.append(f"- Number of days: {len(days)} (expected {n_days}) = {'PASS' if num_days_ok else 'FAIL'}")
    for r in required_per_day:
        missing_days = [dd[0] for dd in per_day_detail if r.lower().strip() in [m.lower() for m in dd[2]]]
        md.append(f"- Per-day requirement '{r}': {'PASS (every day)' if not missing_days else 'FAIL (missing days '+str(missing_days)+')'}")
    for r, found in total_detail:
        md.append(f"- Overall requirement '{r}': {'PASS' if found else 'FAIL'}")
    result = "\n".join(md)

    all_ok = bool(budget_ok and travel_ok and num_days_ok and per_day_ok and total_ok)
    ver = {
        "all_constraints_met": all_ok,
        "budget_total_usd": total_cost, "budget_limit": budget, "within_budget": budget_ok,
        "total_travel_time_hours": round(total_travel_min / 60.0, 2), "travel_limit_minutes": travel_limit, "within_travel_limit": travel_ok,
        "num_days": len(days), "num_days_ok": num_days_ok,
        "required_per_day": required_per_day, "per_day_ok": per_day_ok,
        "required_total": required_total, "total_ok": total_ok,
    }
    plan_doc = result + "\n\n---\n### Verification (automated)\n" + json.dumps(ver, indent=2)
    try:
        with open("itinerary.md", "w") as f:
            f.write(plan_doc)
        with open("travel_evidence.json", "w") as f:
            json.dump({"constraints": constraints, "evidence": dedup, "documents": [{"url": d["url"], "title": d["title"]} for d in all_docs], "log": all_log}, f, indent=2, ensure_ascii=False)
    except Exception as e:
        all_log.append(f"save error: {e}")

    summary = call_llm(
        system="You are a research summarizer. Write a detailed SUMMARY (150-1200 words) consistent with the final plan text provided. Trace the searches run, documents fetched, key numeric evidence (fees/minutes/prices), and the computed totals verified against constraints. Describe the SAME itinerary that appears in the plan.",
        messages=[{"role": "user", "content": f"Request: {query}\n\nConstraints parsed: {json.dumps(constraints)}\n\nFINAL PLAN (authoritative):\n{result}\n\nSearch log:\n" + "\n".join(all_log) + f"\n\nDocuments: {len(all_docs)}\nEvidence: {len(dedup)}\nVerification: {json.dumps(ver)}\n\nWrite the SUMMARY consistent with the FINAL PLAN above."}],
        max_tokens=2500,
    )
    return {"answer": plan_doc, "summary": summary}