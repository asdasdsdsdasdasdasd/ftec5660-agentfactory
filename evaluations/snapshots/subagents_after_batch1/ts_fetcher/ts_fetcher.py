import json
import re
from llm import call_llm
from tools import search_serper, read_url_jina


def _parse_json(text):
    if text is None:
        return None
    t = str(text).strip()
    t = re.sub(r'^```(?:json)?', '', t).strip()
    t = re.sub(r'```$', '', t).strip()
    try:
        return json.loads(t)
    except Exception:
        pass
    m = re.search(r'[\[\{].*[\]\}]', t, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


def main(query: str) -> dict:
    logic = []
    plan = call_llm(
        system=(
            "You are a data research planner. The user wants numeric time-series "
            "indicators (e.g., annual expenditure and GDP by year). Return ONLY a JSON "
            "object with keys: 'series' (list of objects each with name and unit), "
            "'year_range' (object with start and end integers), and 'queries' (list of "
            "4-6 diverse specific web search queries that surface authoritative numeric "
            "data, preferring statistical bureaus, World Bank, official datasets, or "
            "wikipedia tables)."
        ),
        messages=[{"role": "user", "content": "Data request: " + query}],
        max_tokens=1000,
    )
    pj = _parse_json(plan) or {}
    series = pj.get("series", [])
    if not series:
        series = [{"name": query, "unit": ""}]
    queries = pj.get("queries", [query])
    year_range = pj.get("year_range", {"start": 1990, "end": 2024})
    logic.append("Planned series=" + str(series) + " year_range=" + str(year_range))

    seen = set()
    candidates = []
    for q in queries:
        try:
            results = search_serper(q, topk=8)
        except Exception as e:
            logic.append("search failed: " + str(e))
            continue
        if results and "error" in results[0]:
            logic.append("search error: " + str(results[0]["error"]))
            continue
        for r in results:
            link = r.get("link")
            if link and link not in seen:
                seen.add(link)
                candidates.append(r)
        logic.append("query -> " + str(len(results)) + " results")

    series_names = [s.get("name", "") for s in series]
    collected = {}
    evidence_notes = []
    for r in candidates[:12]:
        url = r.get("link")
        if not url:
            continue
        try:
            content = read_url_jina(url)
        except Exception as e:
            continue
        text = content if isinstance(content, str) else (content.get("text", "") if isinstance(content, dict) else "")
        if not text:
            continue
        extract = call_llm(
            system=(
                "You extract numeric time-series data from ONE web document. "
                "Return ONLY a JSON object with key 'series' = a list of objects each with: "
                "name (must match one of the requested series names), unit, and values "
                "(object mapping YEAR string like 2015 to NUMERIC value). Only include values "
                "actually seen in the document. Also include source_note. If no usable data, "
                "return a JSON object whose series is an empty list. Return ONLY valid JSON."
            ),
            messages=[{"role": "user", "content": "Requested series: " + str(series_names) + " Year range: " + str(year_range) + " URL: " + url + " Title: " + str(r.get("title", "")) + " Content:\n" + text[:7000]}],
            max_tokens=3000,
        )
        ex = _parse_json(extract)
        if not isinstance(ex, dict):
            continue
        got_any = False
        for s in ex.get("series", []) or []:
            if not isinstance(s, dict):
                continue
            name = s.get("name", "")
            match = None
            for rn in series_names:
                if rn and (rn.lower() in name.lower() or name.lower() in rn.lower()):
                    match = rn
                    break
            if not match:
                continue
            vals = s.get("values", {}) or {}
            for yr, val in vals.items():
                try:
                    y = int(str(yr).strip())
                    v = float(str(val).replace(",", "").strip())
                except Exception:
                    continue
                collected.setdefault(match, {})
                if y not in collected[match]:
                    collected[match][y] = v
                    got_any = True
        if got_any:
            evidence_notes.append(url + ": " + str(ex.get("source_note", ""))[:200])
            logic.append("extracted from " + url)

    raw_dump = json.dumps(collected, ensure_ascii=False)
    normalize = call_llm(
        system=(
            "You normalize numeric time-series data that may come from multiple sources "
            "with inconsistent units. For each series, convert all values to a SINGLE "
            "consistent unit (choose the most common one; fix obvious 亿元 vs 万亿 mixes). "
            "Return ONLY a JSON object with key 'series' = list of objects each with name, "
            "unit, and values (object mapping YEAR string to NUMERIC value, same unit). "
            "Include notes describing corrections. Return ONLY valid JSON."
        ),
        messages=[{"role": "user", "content": "Requested series: " + str(series_names) + " Raw data:\n" + raw_dump + "\nNotes:\n" + "\n".join(evidence_notes)}],
        max_tokens=3000,
    )
    norm = _parse_json(normalize) or {"series": []}
    final_series = norm.get("series", [])

    start = year_range.get("start", 0) if isinstance(year_range, dict) else 0
    end = year_range.get("end", 9999) if isinstance(year_range, dict) else 9999
    data_out = {"query": query, "year_range": year_range, "series": [], "notes": norm.get("notes", "")}
    for s in final_series:
        if not isinstance(s, dict):
            continue
        vals = {}
        for yr, val in (s.get("values") or {}).items():
            try:
                y = int(str(yr).strip())
                v = float(str(val).replace(",", "").strip())
            except Exception:
                continue
            if start <= y <= end:
                vals[str(y)] = v
        if vals:
            data_out["series"].append({"name": s.get("name", ""), "unit": s.get("unit", ""), "values": vals})

    with open("series_data.json", "w") as f:
        json.dump(data_out, f, indent=2, ensure_ascii=False)

    n_points = sum(len(s["values"]) for s in data_out["series"])
    answer = "Collected " + str(len(data_out["series"])) + " series with " + str(n_points) + " total points. Saved to series_data.json."
    for s in data_out["series"]:
        yrs = sorted(int(y) for y in s["values"])
        if yrs:
            answer += " | " + s["name"] + " (" + s["unit"] + "): " + str(len(yrs)) + " points, years " + str(yrs[0]) + "-" + str(yrs[-1])

    summary = call_llm(
        system="You are a data research summarizer. Write a detailed SUMMARY (100-2000 words) tracing what was searched, what was found, and the numeric data collected.",
        messages=[{"role": "user", "content": "Data request: " + query + " Plan: " + str(series_names) + " Log:\n" + "\n".join(logic) + "\n\nFinal data:\n" + json.dumps(data_out, ensure_ascii=False)[:4000] + "\n\nWrite the SUMMARY."}],
        max_tokens=2000,
    )
    return {"answer": answer, "summary": summary}
