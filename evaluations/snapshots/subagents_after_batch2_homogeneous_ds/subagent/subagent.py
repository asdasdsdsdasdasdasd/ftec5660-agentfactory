import json
import re
import urllib.request
from llm import call_llm


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


def _http_get(url, timeout=40):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode('utf-8', errors='replace')


def _wb_fetch_multi(code, countries, start, end):
    cstr = ';'.join(countries)
    url = ('https://api.worldbank.org/v2/country/' + cstr + '/indicator/' + code +
           '?format=json&per_page=20000&date=' + str(start) + ':' + str(end))
    raw = _http_get(url)
    data = json.loads(raw)
    out = {}
    if isinstance(data, list) and len(data) >= 2 and data[1]:
        for item in data[1]:
            val = item.get('value')
            yr = item.get('date')
            c = item.get('countryiso3code') or (item.get('country') or {}).get('id')
            if val is not None and yr and c:
                out.setdefault(c, {})
                try:
                    out[c][str(int(yr))] = float(val)
                except Exception:
                    pass
    return out


def main(query: str) -> dict:
    logic = []
    plan = call_llm(
        system=(
            'You map a country-indicator data request to World Bank Open Data API '
            'parameters. Return ONLY a JSON object with keys: countries (list of '
            '3-letter ISO country codes), year_range (object with start and end '
            'integers), and indicators (list of objects each with name and wb_code '
            '(real World Bank indicator code) and unit). Common codes: '
            'NY.GDP.PCAP.CD = GDP per capita current US$; NY.GDP.PCAP.PP.CD = GDP per '
            'capita PPP; SP.DYN.LE00.IN = life expectancy at birth years; '
            'NY.GDP.MKTP.CD = GDP current US$; SP.POP.TOTL = population. Choose codes '
            'that precisely match what is requested. Return ONLY valid JSON.'
        ),
        messages=[{'role': 'user', 'content': 'Data request: ' + query}],
        max_tokens=1200,
    )
    pj = _parse_json(plan) or {}
    countries = pj.get('countries') or []
    yr = pj.get('year_range') or {'start': 1990, 'end': 2023}
    indicators = pj.get('indicators') or []
    if not countries:
        countries = ['USA']
    if not indicators:
        indicators = [{'name': 'GDP per capita', 'wb_code': 'NY.GDP.PCAP.CD', 'unit': 'current US$'}]
    start = int(yr.get('start', 1990))
    end = int(yr.get('end', 2023))
    logic.append('Plan countries=' + str(countries) + ' indicators=' + str(indicators) + ' range=' + str(start) + '-' + str(end))

    result = {'query': query, 'countries': countries, 'year_range': {'start': start, 'end': end}, 'indicators': []}
    for ind in indicators:
        code = ind.get('wb_code')
        if not code:
            continue
        try:
            vals = _wb_fetch_multi(code, countries, start, end)
            result['indicators'].append({'name': ind.get('name', code), 'wb_code': code, 'unit': ind.get('unit', ''), 'data': vals})
            logic.append('WB ' + str(code) + ' -> ' + str({c: len(v) for c, v in vals.items()}))
        except Exception as e:
            logic.append('WB ' + str(code) + ' failed: ' + str(e))

    latest = {}
    for ind in result['indicators']:
        for c, years in ind['data'].items():
            if years:
                last_yr = max(years, key=lambda y: int(y))
                latest.setdefault(c, {})[ind['name']] = {'year': last_yr, 'value': years[last_yr]}
    result['latest_values'] = latest

    with open('wb_multi_data.json', 'w') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    summary = call_llm(
        system='You are a data research summarizer. Write a detailed SUMMARY (100-2000 words) of what was fetched from the World Bank API, which countries have data, the latest values, and any gaps.',
        messages=[{'role': 'user', 'content': 'Query: ' + query + '\nLog:\n' + '\n'.join(logic) + '\nLatest values:\n' + json.dumps(latest, ensure_ascii=False)[:5000] + '\n\nWrite SUMMARY.'}],
        max_tokens=2000,
    )

    n_ind = len(result['indicators'])
    n_ctry = len([c for c in latest if latest[c]])
    answer = ('Fetched ' + str(n_ind) + ' indicators from World Bank API for ' + str(n_ctry) +
              ' countries. Saved wb_multi_data.json.')
    return {'answer': answer, 'summary': summary}
