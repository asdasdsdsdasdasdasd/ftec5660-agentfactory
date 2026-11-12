import json
import re
import os
from llm import call_llm


def _parse_json(t):
    t = t.strip()
    t = re.sub(r'^```(?:json)?', '', t).strip()
    t = re.sub(r'```$', '', t).strip()
    try:
        return json.loads(t)
    except Exception:
        m = re.search(r'\{.*\}', t, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


def main(query: str) -> dict:
    plan = call_llm(
        system=('You are a data extraction planner. Given a request to build a numeric time series for charting, '
                'return ONLY a JSON object with keys: source_file (path to a JSON evidence file, or empty), '
                'metric (what quantity to extract), unit (unit of metric), chart_title (concise title). Return ONLY valid JSON.'),
        messages=[{'role': 'user', 'content': 'Request: ' + query}],
        max_tokens=500,
    )
    pj = _parse_json(plan) or {}
    source_file = pj.get('source_file') or 'evidence.json'
    metric = pj.get('metric', query)
    unit = pj.get('unit', '%')
    chart_title = pj.get('chart_title', metric)

    payload_text = ''
    if source_file and os.path.exists(source_file):
        try:
            with open(source_file) as f:
                data = json.load(f)
            payload_text = json.dumps(data, ensure_ascii=False)[:60000]
        except Exception as e:
            payload_text = 'failed to load ' + source_file + ': ' + str(e)
    else:
        payload_text = query

    sys2 = ('You are a meticulous data analyst. From the provided evidence text, extract a time series of '
            'numeric data points for the metric: ' + metric + ' (unit: ' + str(unit) + '). '
            'Each point must have integer year and numeric value, plus short source and note. '
            'Only include data explicitly supported by the evidence (no fabrication). '
            'IMPORTANT: If the request asks to build a representative trajectory across time, you MAY combine '
            'single-year data points from DIFFERENT studies/sources into ONE series, as long as each point reflects '
            'a comparable concept (e.g. percent considering/buying an EV, or favorability percent). Record the source '
            'of each point. Only use years that actually have a reported value; do NOT invent values for missing years. '
            'Prefer ONE representative series across the widest year span; optionally a 2nd series. '
            'Return ONLY JSON: {"series":[{"name":"...","points":[{"year":2018,"value":16,"source":"...","note":"..."}]}],"summary_notes":"..."}. '
            'Sort points by year. Return ONLY JSON.')
    extract = call_llm(
        system=sys2,
        messages=[{'role': 'user', 'content': 'Metric: ' + metric + '\n\nEvidence text:\n' + payload_text}],
        max_tokens=3000,
    )
    parsed = _parse_json(extract)
    if not parsed or 'series' not in parsed:
        return {'answer': 'Failed to extract numeric time series.',
                'summary': 'Could not parse extraction. Raw: ' + extract[:500]}

    clean_series = []
    for s in parsed.get('series', []):
        pts = []
        for p in s.get('points', []):
            try:
                y = int(p.get('year'))
                v = float(p.get('value'))
            except Exception:
                continue
            pts.append({'year': y, 'value': v, 'source': str(p.get('source', '')), 'note': str(p.get('note', ''))})
        pts.sort(key=lambda x: x['year'])
        if pts:
            clean_series.append({'name': str(s.get('name', 'Series')), 'points': pts})

    if not clean_series:
        return {'answer': 'No valid data points.', 'summary': 'No valid points. Notes: ' + str(parsed.get('summary_notes', ''))}

    out = {'metric': metric, 'unit': unit, 'chart_title': chart_title,
           'series': clean_series, 'summary_notes': parsed.get('summary_notes', '')}
    with open('timeseries.json', 'w') as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    lines = ['Extracted time series for ' + metric + ' (unit ' + str(unit) + '):']
    for s in clean_series:
        pts_str = ', '.join(str(p['year']) + ':' + str(p['value']) for p in s['points'])
        lines.append('- ' + s['name'] + ': ' + pts_str)
    answer = '\n'.join(lines)

    summary = call_llm(
        system='Write a concise SUMMARY (100-400 words) of how the numeric time series was extracted, what points were found and their sources, and caveats.',
        messages=[{'role': 'user', 'content': 'Request: ' + query + '\nExtracted:\n' + json.dumps(out, ensure_ascii=False) + '\n\nWrite the SUMMARY.'}],
        max_tokens=1000,
    )
    return {'answer': answer, 'summary': summary}
