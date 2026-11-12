import json
import re
from llm import call_llm
from tools import search_serper, read_url_jina


def _clean_json(text):
    if not text:
        return None
    t = text.strip()
    t = re.sub(r'^```(?:json)?', '', t).strip()
    t = re.sub(r'```$', '', t).strip()
    m = re.search(r'\{.*\}', t, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    try:
        return json.loads(t)
    except Exception:
        return None


def _fetch(url):
    try:
        content = read_url_jina(url)
    except Exception as e:
        return '', str(e)
    if isinstance(content, dict):
        if 'error' in content:
            return '', str(content.get('error'))
        return content.get('text', '') or '', None
    if isinstance(content, str):
        return content, None
    return '', 'unknown'


def main(query: str) -> dict:
    log = []
    # 1) Plan the task: what entity/org, preferred domain, candidate URLs, search queries
    plan_raw = call_llm(
        system=(
            "You are a web research planner. Given a task about finding an ORGANIZATION or entity's official web page "
            "and extracting its description plus a list of its repositories/items, output ONLY a JSON object with keys: "
            "'entity' (the org/entity name), 'preferred_domain' (domain substring like github.com, wikipedia.org, or ''), "
            "'search_queries' (3-5 specific concrete search queries), "
            "'candidate_urls' (2-5 likely DIRECT URLs of the official page, e.g. https://github.com/facebookresearch; best guess first), "
            "'description_target' (what description to extract), "
            "'list_target' (what list of items/repos to extract and minimum count if stated), "
            "'output_file' (markdown filename ending .md). Return ONLY valid JSON."
        ),
        messages=[{'role': 'user', 'content': 'Task: ' + query}],
        max_tokens=900,
    )
    plan = _clean_json(plan_raw) or {}
    entity = plan.get('entity', '')
    preferred = (plan.get('preferred_domain') or '').strip().lower()
    search_queries = plan.get('search_queries') or [query]
    candidate_urls = plan.get('candidate_urls') or []
    desc_target = plan.get('description_target', 'the page description / overview')
    list_target = plan.get('list_target', 'a list of main repositories/items')
    output_file = plan.get('output_file') or 'org_report.md'
    if not output_file.endswith('.md'):
        output_file += '.md'
    log.append('Plan entity=' + entity + ' preferred=' + preferred)
    log.append('Candidate URLs=' + str(candidate_urls))
    log.append('Search queries=' + str(search_queries))

    # 2) Build ordering: try direct candidate URLs first, then search results
    ordered = []
    seen = set()
    for u in candidate_urls:
        if u and u not in seen:
            seen.add(u)
            ordered.append(u)
    # 3) Run searches to find more candidates
    search_jobs = list(search_queries)
    if preferred:
        for q in list(search_queries):
            search_jobs.append(q + ' site:' + preferred)
    for q in search_jobs:
        try:
            results = search_serper(q, topk=8)
        except Exception as e:
            log.append('Search err ' + q + ': ' + str(e))
            continue
        if results and isinstance(results, list) and 'error' in results[0]:
            log.append('Search err ' + q + ': ' + str(results[0]['error']))
            continue
        n = 0
        for r in results:
            link = r.get('link')
            if link and link not in seen:
                seen.add(link)
                ordered.append(link)
                n += 1
        log.append('Search ' + q + ' -> ' + str(n) + ' new links')

    # 4) Fetch pages in order; score how good each is for the task
    best_text = ''
    best_url = ''
    evidence = []
    max_fetch = 12
    for url in ordered[:max_fetch]:
        txt, err = _fetch(url)
        if err or not txt or len(txt) < 150:
            log.append('Skip ' + url + ' (' + str(err or 'short ' + str(len(txt) if txt else 0)) + ')')
            continue
        # quick quality check
        check = call_llm(
            system="You check whether a fetched web page is the OFFICIAL page for a given entity and contains the needed description + list of repos/items. Return ONLY JSON: {\"match\": <0-10 int>, \"has_list\": <true/false>, \"reason\": \"<short>\"}",
            messages=[{'role': 'user', 'content': 'Entity: ' + entity + '\nURL: ' + url + '\nNeeded: ' + desc_target + ' AND ' + list_target + '\n\nPage excerpt:\n' + txt[:3500]}],
            max_tokens=200,
        )
        cj = _clean_json(check) or {}
        score = cj.get('match', 0)
        has_list = cj.get('has_list', False)
        log.append('Check ' + url + ' -> score=' + str(score) + ' has_list=' + str(has_list) + ' (' + str(cj.get('reason','')) + ')')
        evidence.append({'url': url, 'score': score, 'has_list': has_list, 'len': len(txt)})
        if score >= 6 and has_list and (not best_text or score > max([e['score'] for e in evidence if e['url']==best_url], default=0)):
            best_text = txt
            best_url = url
            # keep going a little to find the best, but if very strong stop
            if score >= 8:
                break

    if not best_text:
        # fallback: use the longest fetched page
        for e in evidence:
            log.append('Fallback candidate ' + e['url'] + ' score=' + str(e['score']))
        # re-fetch the highest scored
        if evidence:
            evidence.sort(key=lambda x: (x['score'], x['has_list'], x['len']), reverse=True)
            best_url = evidence[0]['url']
            best_text, _ = _fetch(best_url)
            log.append('Fallback to ' + best_url)

    if not best_text:
        summary = call_llm(
            system='Write a SUMMARY explaining the research attempt and why it failed.',
            messages=[{'role': 'user', 'content': 'Task: ' + query + '\nLog:\n' + '\n'.join(log)}],
            max_tokens=800,
        )
        return {'answer': 'Failed to fetch a suitable official page for: ' + entity, 'summary': summary}

    # 5) Extract description + list of repos/items
    ext_raw = call_llm(
        system=(
            "You are an expert reader. From the web page content, produce ONLY a JSON object with keys: "
            "'title' (page/org name), 'description' (a faithful, concise description of the organization/page, 2-5 sentences, only from the page), "
            "'repos' (a list of objects each with 'name' and 'description' — the main repositories/items found ON THE PAGE; include ALL clearly-listed repos, at least as many as the page shows, each description short), "
            "'notes' (any caveats). Only use information present in the page content. Return ONLY valid JSON."
        ),
        messages=[{'role': 'user', 'content': 'Extract: ' + desc_target + '\nAnd: ' + list_target + '\nPage URL: ' + best_url + '\n\nPage content:\n' + best_text[:20000]}],
        max_tokens=3000,
    )
    ext = _clean_json(ext_raw) or {}
    title = ext.get('title') or entity
    description = ext.get('description', '')
    repos = ext.get('repos', []) or []
    notes = ext.get('notes', '')

    # 6) Write markdown
    md = []
    md.append('# ' + str(title) + '\n')
    md.append('**Source page:** ' + best_url + '\n')
    md.append('## Description\n')
    md.append((description or '_Not found._') + '\n')
    md.append('## Main Repositories\n')
    if repos:
        md.append('| Repository | Description |')
        md.append('| --- | --- |')
        for r in repos:
            nm = str(r.get('name', '')).replace('|', '\\|')
            ds = str(r.get('description', '')).replace('|', '\\|')
            md.append('| ' + nm + ' | ' + ds + ' |')
        md.append('')
    else:
        md.append('_No repositories found._\n')
    if notes:
        md.append('## Notes\n')
        md.append(str(notes) + '\n')
    md_text = '\n'.join(md)
    with open(output_file, 'w') as f:
        f.write(md_text)
    log.append('Wrote ' + output_file + ' with ' + str(len(repos)) + ' repos')

    summary = call_llm(
        system='Write a detailed SUMMARY (100-2000 words) tracing what was searched, which URL was chosen as the official page, what description and how many repos were extracted, and how the markdown was produced.',
        messages=[{'role': 'user', 'content': 'Task: ' + query + '\nLog:\n' + '\n'.join(log) + '\n\nChosen URL: ' + best_url + '\nDescription: ' + description[:500] + '\nRepos count: ' + str(len(repos)) + '\nRepo names: ' + str([r.get('name') for r in repos]) + '\nOutput: ' + output_file}],
        max_tokens=2000,
    )
    answer = 'Opened official page ' + best_url + '. Description extracted. ' + str(len(repos)) + ' repositories listed. Saved to ' + output_file + '.'
    return {'answer': answer, 'summary': summary}
