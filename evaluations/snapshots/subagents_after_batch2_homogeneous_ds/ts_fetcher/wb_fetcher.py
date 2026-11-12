import json
import re
import urllib.request
import urllib.parse
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


def _http_get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _wb_fetch(code, country, start, end):
    url = ("https://api.worldbank.org/v2/country/" + country + "/indicator/" + code +
           "?format=json&per_page=2000&date=" + str(start) + ":" + str(end))
    raw = _http_get(url)
    data = json.loads(raw)
    out = {}
    if isinstance(data, list) and len(data) >= 2 and data[1]:
        for item in data[1]:
            val = item.get("value")
            yr = item.get("date")
            if val is not None and yr:
                try:
                    out[str(int(yr))] = float(val)
                except Exception:
                    pass
    return out


def main(query: str) -> dict:
    logic = []
    # Step 1: LLM maps request -> World Bank country code + indicator codes
    plan = call_llm(
        system=(
            "You map a country-indicator data request to World Bank Open Data API "
            "parameters. Return ONLY a JSON object with keys: 'country' (3-letter ISO "
            "country code), 'year_range' (object start,end), and 'indicators' (list of "
            "objects each with 'name', 'wb_code' (the World Bank indicator code), and "
            "'unit'). Choose real World Bank indicator codes, e.g. 'NY.GDP.MKTP.CD' for "
            "GDP current US$, 'NY.GDP.MKTP.CN' for GDP current LCU, 'SE.XPD.TOTL.GD.ZS' for "
            "government expenditure on education (% of GDP), 'SE.XPD.TOTL.GB.ZS' for "
            "education expenditure (% of government expenditure). If the user wants an "
            "absolute education expenditure figure, collect BOTH education-percent-of-GDP "
            "and GDP in the same currency so it can be derived later. Return ONLY valid JSON."
        ),
        messages=[{"role": "user", "content": "Data request: " + query}],
        max_tokens=1000,
    )
    pj = _parse_json(plan) or {}
    country = pj.get("country", "CHN")
    yr = pj.get("year_range", {"start": 2000, "end": 2023})
    indicators = pj.get("indicators", [])
    if not indicators:
        indicators = [{"name": "GDP", "wb_code": "NY.GDP.MKTP.CD", "unit": "USD"}]
    start, end = yr.get("start", 2000), yr.get("end", 2023)
    logic.append("Plan country=" + str(country) + " indicators=" + str(indicators) + " range=" + str(start) + "-" + str(end))

    # Step 2: fetch each indicator from World Bank
    fetched = {}
    for ind in indicators:
        code = ind.get("wb_code")
        if not code:
            continue
        try:
            vals = _wb_fetch(code, country, start, end)
            fetched[ind.get("name", code)] = {"wb_code": code, "unit": ind.get("unit", ""), "values": vals}
            logic.append("WB " + str(code) + " -> " + str(len(vals)) + " points")
        except Exception as e:
            logic.append("WB " + str(code) + " failed: " + str(e))

    # Step 3: LLM derives any requested absolute figures from base series
    derive = call_llm(
        system=(
            "You are a data assistant. Given base series fetched from World Bank (each with "
            "unit and year->value), the user originally asked for certain indicators. "
            "Produce the final requested series. You may derive new series by multiplying "
            "a percent series by a GDP series (divide percent by 100). Return ONLY a JSON "
            "object with key 'series' = list of objects each with 'name', 'unit', and "
            "'values' (object mapping YEAR string to NUMERIC value). Only include years "
            "where data is valid. Return ONLY valid JSON."
        ),
        messages=[{"role": "user", "content": "Original request: " + query + "\n\nBase series fetched:\n" + json.dumps(fetched, ensure_ascii=False)}],
        max_tokens=3000,
    )
    derived = _parse_json(derive) or {"series": []}
    final_series = derived.get("series", [])
    if not final_series:
        for name, d in fetched.items():
            if d["values"]:
                final_series.append({"name": name, "unit": d["unit"], "values": d["values"]})

    data_out = {"query": query, "country": country, "series": []}
    for s in final_series:
        if not isinstance(s, dict):
            continue
        vals = {}
        for y, v in (s.get("values") or {}).items():
            try:
                vals[str(int(float(y)))] = float(str(v).replace(",", ""))
            except Exception:
                continue
        if vals:
            data_out["series"].append({"name": s.get("name", ""), "unit": s.get("unit", ""), "values": vals})

    with open("series_data.json", "w") as f:
        json.dump(data_out, f, indent=2, ensure_ascii=False)

    n_points = sum(len(s["values"]) for s in data_out["series"])
    answer = "World Bank data: " + str(len(data_out["series"])) + " series, " + str(n_points) + " points. Saved series_data.json."
    for s in data_out["series"]:
        yrs = sorted(int(y) for y in s["values"])
        if yrs:
            answer += " | " + s["name"] + " (" + str(s["unit"]) + "): " + str(len(yrs)) + " pts " + str(yrs[0]) + "-" + str(yrs[-1])

    summary = call_llm(
        system="You are a data research summarizer. Write a detailed SUMMARY of what was fetched from World Bank and how derived series were computed.",
        messages=[{"role": "user", "content": "Query: " + query + " Log:\n" + "\n".join(logic) + "\nFinal data:\n" + json.dumps(data_out, ensure_ascii=False)[:4000] + "\n\nWrite SUMMARY."}],
        max_tokens=2000,
    )
    return {"answer": answer, "summary": summary}
