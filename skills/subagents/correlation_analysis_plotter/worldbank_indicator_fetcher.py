import json, urllib.request, urllib.parse
from llm import call_llm


def _get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def main(query: str) -> dict:
    plan_prompt = (
        "You are a data acquisition planner. Parse the user's request for country-level "
        "statistics into a JSON plan. Output ONLY valid JSON (no markdown, no code fences).\n"
        "Schema:\n"
        "{\"indicators\": [{\"name\": \"human friendly name\", \"wb_code\": \"World Bank indicator code\"}], "
        "\"countries\": [{\"name\": \"Country Name\", \"iso3\": \"ISO3 code\"}], "
        "\"year\": <integer year or null for latest> }\n"
        "Guidance for World Bank indicator codes:\n"
        "- GDP per capita (current US$): NY.GDP.PCAP.CD\n"
        "- GDP per capita (constant 2015 US$): NY.GDP.PCAP.KD\n"
        "- Life expectancy at birth (years): SP.DYN.LE00.IN\n"
        "- Population, total: SP.POP.TOTL\n"
        "- Health expenditure per capita (current US$): SH.XPD.CHEX.PC.CD\n"
        "- Under-5 mortality rate: SH.DYN.MORT\n"
        "Use the most appropriate World Bank codes for what the user asks. If the user asks for 'at least N "
        "countries' and does not name specific ones, choose a diverse representative set of about 10 well-known "
        "countries spanning low, middle, and high income levels. Use ISO3 codes. If no year is specified, "
        "use null so we pick the latest common year automatically.\n\n"
        "User request:\n" + query
    )
    plan_raw = call_llm(
        system="You convert data requests into a strict JSON acquisition plan. Output JSON only.",
        messages=[{"role": "user", "content": plan_prompt}],
    )
    plan = None
    try:
        plan = json.loads(plan_raw)
    except Exception:
        s = plan_raw.find("{"); e = plan_raw.rfind("}")
        if s != -1 and e != -1:
            try:
                plan = json.loads(plan_raw[s:e + 1])
            except Exception:
                plan = None
    if not plan or not plan.get("indicators") or not plan.get("countries"):
        return {"answer": "Failed to parse data acquisition plan.", "summary": "LLM plan parse failed. Raw: " + str(plan_raw)[:800]}

    indicators = plan["indicators"]
    countries = plan["countries"]
    year = plan.get("year")
    iso_list = ";".join([c["iso3"] for c in countries if c.get("iso3")])
    name_map = {c["iso3"]: c["name"] for c in countries if c.get("iso3")}

    per_indicator = {}
    log = []
    for ind in indicators:
        code = ind.get("wb_code")
        iname = ind.get("name", code)
        if not code:
            continue
        url = ("https://api.worldbank.org/v2/country/" + urllib.parse.quote(iso_list) +
               "/indicator/" + urllib.parse.quote(code) + "?format=json&per_page=20000")
        if year:
            url += "&date=" + str(year)
        try:
            data = _get_json(url)
        except Exception as ex:
            log.append("Fetch error for %s: %s" % (code, ex)); continue
        if not isinstance(data, list) or len(data) < 2 or not data[1]:
            log.append("No data for %s" % code); continue
        for row in data[1]:
            iso = row.get("countryiso3code") or (row.get("country") or {}).get("id")
            val = row.get("value"); yr = row.get("date")
            if iso and val is not None:
                per_indicator.setdefault(iso, {}).setdefault(code, []).append((int(yr), val, iname))
        log.append("Fetched %s (%d raw rows)" % (code, len(data[1])))

    codes = [i["wb_code"] for i in indicators if i.get("wb_code")]
    name_by_code = {i["wb_code"]: i.get("name", i["wb_code"]) for i in indicators if i.get("wb_code")}
    records = []
    for iso, indmap in per_indicator.items():
        if year:
            ty = int(year)
            rec = {"country": name_map.get(iso, iso), "iso3": iso, "year": ty}; ok = True
            for code in codes:
                m = [v for (y, v, _) in indmap.get(code, []) if y == ty]
                if m: rec[name_by_code[code]] = m[0]
                else: ok = False
            if ok: records.append(rec)
        else:
            ys = [{y for (y, v, _) in indmap.get(code, [])} for code in codes]
            if not ys or any(not s for s in ys): continue
            common = set.intersection(*ys)
            if not common: continue
            ty = max(common)
            rec = {"country": name_map.get(iso, iso), "iso3": iso, "year": ty}
            for code in codes:
                m = [v for (y, v, _) in indmap.get(code, []) if y == ty]
                rec[name_by_code[code]] = m[0]
            records.append(rec)

    if codes:
        records.sort(key=lambda r: r.get(name_by_code.get(codes[0]), 0) or 0, reverse=True)
    out = {"records": records, "indicators": indicators, "year_requested": year, "source": "World Bank Open Data API (api.worldbank.org)", "log": log}
    with open("wb_data.json", "w") as f:
        json.dump(out, f, indent=2)

    summary = call_llm(
        system="You are a data summarizer. Write a concise but complete SUMMARY of the data acquisition.",
        messages=[{"role": "user", "content": (
            "Query: " + query + "\n\nPlan indicators: " + json.dumps(indicators) +
            "\nCountries: " + json.dumps([c.get('name') for c in countries]) +
            "\nLog: " + json.dumps(log) +
            "\nRecords obtained: " + json.dumps(records) + "\n\n"
            "Summarize what was fetched, from World Bank Open Data API, the year(s) used, how many "
            "countries/indicators, and any gaps. Data saved to wb_data.json.")}],
        max_tokens=2000,
    )
    return {"answer": json.dumps(records, indent=2), "summary": summary}
