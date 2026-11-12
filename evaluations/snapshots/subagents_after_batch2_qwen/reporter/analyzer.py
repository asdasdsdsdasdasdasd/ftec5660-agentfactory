import json
import re
from llm import call_llm


def main(query: str) -> dict:
    """Generic sentiment-over-time analyzer.
    Reads an evidence JSON file (default 'evidence.json' if present, else the
    file path parsed from the query). Each evidence item is classified into a
    sentiment (positive/neutral/negative) and assigned to a time period. It then
    aggregates counts and a net sentiment score per period and writes
    sentiment_timeline.json.
    """

    # Step 1: locate input file and understand the data
    plan = call_llm(
        system=(
            "Parse this request. Return JSON with keys: 'input_file' (a path to a "
            "json file mentioned, or 'evidence.json' if none mentioned) and "
            "'time_granularity' (one of: year, month, era, decade). Return ONLY "
            "valid JSON."
        ),
        messages=[{"role": "user", "content": query}],
        max_tokens=300,
    )
    try:
        plan_json = json.loads(re.search(r"\{.*\}", plan, re.DOTALL).group(0))
    except Exception:
        plan_json = {"input_file": "evidence.json", "time_granularity": "era"}

    input_file = plan_json.get("input_file", "evidence.json")
    try:
        with open(input_file) as f:
            data = json.load(f)
    except Exception as e:
        return {"answer": f"Could not read {input_file}: {e}", "summary": f"Failed to open input file {input_file}."}

    evidence = data.get("evidence", []) if isinstance(data, dict) else data
    if not isinstance(evidence, list):
        evidence = []

    if not evidence:
        return {"answer": "No evidence items found in input file.", "summary": f"Input {input_file} contained no evidence items."}

    # Step 2: Determine the set of time periods from the evidence dates
    date_hints = [str(e.get("date_hint", "")) for e in evidence if isinstance(e, dict)]
    joined_dates = " | ".join([d for d in date_hints if d])
    period_def = call_llm(
        system=(
            "Given date hints from evidence about a topic, define 5 ordered "
            "time periods (eras or years) that cover the whole range and can be "
            "used to bucket evidence. Return ONLY a JSON object with key 'periods': "
            "an ordered list of objects each with 'label' (short name) and 'range' "
            "(description like '2000-2005' or '2023'). No markdown, no prose. "
            "Return ONLY valid JSON."
        ),
        messages=[{"role": "user", "content": f"Topic focus: {str(data.get('focus','') if isinstance(data,dict) else '')[:800]}\n\nDate hints found: {joined_dates[:3000]}"}],
        max_tokens=700,
    )

    def _parse_obj(text):
        t = text.strip()
        t = re.sub(r"^```(?:json)?", "", t).strip()
        t = re.sub(r"```$", "", t).strip()
        try:
            return json.loads(t)
        except Exception:
            m = re.search(r"\{.*\}", t, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(0))
                except Exception:
                    return None
        return None

    pobj = _parse_obj(period_def)
    periods = []
    if pobj and isinstance(pobj, dict):
        periods = pobj.get("periods", []) or []
    # Filter to well-formed period dicts with non-empty labels
    periods = [p for p in periods if isinstance(p, dict) and str(p.get("label", "")).strip()]

    # Fallback: if LLM failed to define periods, derive a default set of year-range eras
    if not periods:
        years = [int(y) for y in re.findall(r"(19\d{2}|20\d{2})", joined_dates)]
        if years:
            lo, hi = min(years), max(years)
            # 5 evenly spaced eras
            span = max((hi - lo) // 5 + 1, 1)
            eras = []
            start = lo
            while start <= hi:
                end = min(start + span - 1, hi)
                eras.append({"label": f"{start}-{end}", "range": f"{start}-{end}"})
                start = end + 1
            periods = eras[:5] if eras else []
    if not periods:
        # last resort: single broad period so chart still has a point
        periods = [{"label": "All periods", "range": "all"}]

    period_labels = [p.get("label", "") for p in periods]
    periods_help = "\n".join(f"- {p.get('label','')}: {p.get('range','')}" for p in periods)

    # Step 3: Classify each evidence item's sentiment and assign to a period
    # Do it in batches to be efficient
    classified = []
    batch_size = 12
    for start in range(0, len(evidence), batch_size):
        batch = evidence[start:start + batch_size]
        items_str = ""
        for j, e in enumerate(batch):
            if not isinstance(e, dict):
                continue
            items_str += f"\n[{j}] TEXT: {str(e.get('text',''))[:500]}\nDATE_HINT: {e.get('date_hint','')}\n"

        resp = call_llm(
            system=(
                "You classify evidence items about a topic. For each item return its "
                "index and two fields: (1) 'sentiment' = one of positive/negative/neutral, "
                "where positive = optimistic/bullish/favorable sentiment toward the subject, "
                "negative = pessimistic/bearish/critical, neutral = factual/descriptive. "
                "(2) 'period' = the label of the period whose date RANGE best matches any "
                "year mentioned in the item's DATE_HINT or TEXT. If a year in the hint/text "
                "falls within a period's range, assign that period. Only use 'Unknown' if "
                "the item truly has no year/date reference that maps to any range. "
                "Return ONLY a JSON object with key 'results': a list of objects with keys "
                "'i', 'sentiment', 'period'. No markdown, no prose. Return ONLY valid JSON."
            ),
            messages=[{"role": "user", "content": f"Periods (label: year range):\n{periods_help}\n\nClassify these items, mapping each to a period by year:{items_str}"}],
            max_tokens=1500,
        )
        try:
            res = json.loads(re.search(r"\{.*\}", resp, re.DOTALL).group(0)).get("results", [])
        except Exception:
            res = []
        by_idx = {r.get("i"): r for r in res if isinstance(r, dict)}
        for j, e in enumerate(batch):
            if not isinstance(e, dict):
                continue
            r = by_idx.get(j, {})
            senti = str(r.get("sentiment", "neutral")).lower()
            if senti not in ("positive", "negative", "neutral"):
                senti = "neutral"
            period = str(r.get("period", "Unknown"))
            if period_labels and period not in period_labels:
                period = "Unknown"
            classified.append({
                "period": period,
                "sentiment": senti,
                "text": str(e.get("text", ""))[:400],
                "source": e.get("source", ""),
                "date_hint": e.get("date_hint", ""),
            })

    # Step 4: Aggregate per period
    # preserve order of periods; append Unknown at end
    ordered = list(period_labels)
    seen_periods = set(ordered)
    for c in classified:
        if c["period"] not in seen_periods:
            ordered.append(c["period"])
            seen_periods.add(c["period"])

    timeline = []
    for label in ordered:
        rows = [c for c in classified if c["period"] == label]
        pos = sum(1 for c in rows if c["sentiment"] == "positive")
        neg = sum(1 for c in rows if c["sentiment"] == "negative")
        neu = sum(1 for c in rows if c["sentiment"] == "neutral")
        total = len(rows)
        net = round((pos - neg) / total, 3) if total else 0.0
        timeline.append({
            "period": label,
            "total": total,
            "positive": pos,
            "negative": neg,
            "neutral": neu,
            "net_sentiment": net,
        })

    output = {
        "focus": data.get("focus", "") if isinstance(data, dict) else "",
        "periods_defined": periods,
        "timeline": timeline,
        "classified_items": classified,
    }
    with open("sentiment_timeline.json", "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Summary
    summary = call_llm(
        system="You are an analyst summarizing a sentiment-over-time analysis. Write a detailed SUMMARY (100-2000 words) describing the periods used, the sentiment distribution per period, overall trend, and notable shifts. Include the numeric timeline.",
        messages=[{"role": "user", "content": f"Focus: {output['focus']}\n\nTimeline:\n{json.dumps(timeline, ensure_ascii=False)}\n\nTotal classified items: {len(classified)}\n\nWrite the SUMMARY."}],
        max_tokens=2000,
    )

    trend_desc = "; ".join(f"{t['period']}: net={t['net_sentiment']} (n={t['total']})" for t in timeline if t['total'] > 0)
    return {
        "answer": f"Classified {len(classified)} evidence items across {len([t for t in timeline if t['total']>0])} periods. Trend: {trend_desc}",
        "summary": summary,
    }
