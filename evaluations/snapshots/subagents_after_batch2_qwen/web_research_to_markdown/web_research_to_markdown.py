import json
import re
from llm import call_llm
from tools import search_serper, read_url_jina


def _clean_json(text):
    t = text.strip()
    t = re.sub(r'^```(?:json)?', '', t).strip()
    t = re.sub(r'```$', '', t).strip()
    m = re.search(r'\{.*\}', t, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    try:
        return json.loads(t)
    except Exception:
        return None


def _fetch_text(url):
    try:
        content = read_url_jina(url)
    except Exception as e:
        return '', str(e)
    if isinstance(content, dict):
        if 'error' in content:
            return '', str(content.get('error'))
        return content.get('text', '') or '', None
    return content or '', None


def main(query: str) -> dict:
    log = []

    plan_raw = call_llm(
        system=(
            "You are a research task planner. Given a user research task, output ONLY a JSON object with keys: "
            "'search_queries' (list of 2-4 specific web search queries; if a site like Wikipedia is mentioned include it), "
            "'preferred_site' (domain substring like wikipedia.org if a specific site is requested, else empty string), "
            "'target_page' (short description of exact page/article), "
            "'extract' (what core content to extract), "
            "'summarize' (what ideas to summarize), "
            "'output_file' (a markdown filename ending .md). Return ONLY valid JSON."
        ),
        messages=[{'role': 'user', 'content': 'Research task: ' + query}],
        max_tokens=900,
    )
    plan = _clean_json(plan_raw) or {}
    search_queries = plan.get('search_queries') or [query]
    preferred = (plan.get('preferred_site') or '').strip().lower()
    target_page = plan.get('target_page', query)
    extract = plan.get('extract', 'core definition and key facts')
    summarize = plan.get('summarize', 'main ideas')
    output_file = plan.get('output_file') or 'research_report.md'
    if not output_file.endswith('.md'):
        output_file += '.md'
    log.append('Planned queries: ' + str(search_queries) + ' | preferred: ' + preferred)

    seen = set()
    candidates = []
    search_jobs = list(search_queries)
    if preferred:
        for q in list(search_queries):
            search_jobs.append(q + ' site:' + preferred)
    for q in search_jobs:
        try:
            results = search_serper(q, topk=8)
        except Exception as e:
            log.append('Search ' + q + ' failed: ' + str(e))
            continue
        if results and isinstance(results, list) and 'error' in results[0]:
            log.append('Search ' + q + ' error: ' + str(results[0]['error']))
            continue
        n_new = 0
        for r in results:
            link = r.get('link')
            if link and link not in seen:
                seen.add(link)
                candidates.append(r)
                n_new += 1
        log.append('Search ' + q + ' -> ' + str(len(results)) + ' results, ' + str(n_new) + ' new')

    def pref_rank(c):
        link = (c.get('link') or '').lower()
        return 0 if (preferred and preferred in link) else 1
    candidates.sort(key=pref_rank)
    shortlist = candidates[:12]
    listing = '\n'.join('[' + str(i) + '] ' + str(c.get('title','')) + ' | ' + str(c.get('link','')) + ' | ' + str(c.get('snippet',''))[:160] for i, c in enumerate(shortlist))
    rank_raw = call_llm(
        system="You choose the single BEST web page to open for a research task. Return ONLY a JSON object: {\"index\": <int>, \"reason\": \"<short>\"}.",
        messages=[{'role': 'user', 'content': 'Target page: ' + target_page + '\nTask: ' + query + '\nPrefer domain: ' + preferred + '\n\nCandidates:\n' + listing}],
        max_tokens=300,
    )
    rank = _clean_json(rank_raw) or {}
    best_idx = rank.get('index', 0)
    if not isinstance(best_idx, int) or best_idx < 0 or best_idx >= len(shortlist):
        best_idx = 0
        if preferred:
            for i, c in enumerate(shortlist):
                if preferred in (c.get('link', '').lower()):
                    best_idx = i
                    break
    if shortlist:
        log.append('Chosen index ' + str(best_idx) + ': ' + str(shortlist[best_idx].get('link')))

    page_text = ''
    page_url = ''
    page_title = ''
    order = [best_idx] + [i for i in range(len(shortlist)) if i != best_idx]
    for idx in order:
        c = shortlist[idx]
        url = c.get('link')
        if not url:
            continue
        txt, err = _fetch_text(url)
        if not err and txt and len(txt) > 200:
            page_text = txt
            page_url = url
            page_title = c.get('title', '')
            log.append('Fetched ' + url + ' (' + str(len(txt)) + ' chars)')
            break
        else:
            log.append('Fetch failed/short for ' + str(url) + ': ' + str(err or 'too short'))

    if not page_text:
        summary = call_llm(
            system='Write a SUMMARY of the research attempt and why it failed.',
            messages=[{'role': 'user', 'content': 'Task: ' + query + '\nLog:\n' + '\n'.join(log)}],
            max_tokens=800,
        )
        return {'answer': 'Failed to fetch a suitable page.', 'summary': summary}

    extract_raw = call_llm(
        system=(
            "You are an expert reader. From the provided web page content, produce ONLY a JSON object with keys: "
            "'title' (page title), 'core_definition' (faithful concise statement of requested core content), "
            "'summary' (well-structured markdown summary 150-400 words covering requested ideas), "
            "'key_points' (list of 3-7 short bullet strings). Only use information in the page. Return ONLY valid JSON."
        ),
        messages=[{'role': 'user', 'content': 'Task: ' + query + '\nExtract: ' + extract + '\nSummarize: ' + summarize + '\n\nPage URL: ' + page_url + '\nPage content:\n' + page_text[:12000]}],
        max_tokens=2000,
    )
    extracted = _clean_json(extract_raw) or {}
    page_title_final = extracted.get('title') or page_title
    core_definition = extracted.get('core_definition', '')
    summary_body = extracted.get('summary', '')
    key_points = extracted.get('key_points', []) or []

    md = []
    md.append('# ' + str(page_title_final) + '\n')
    md.append('**Source:** ' + page_url + '\n')
    md.append('**Task:** ' + query + '\n')
    md.append('## Core Definition\n')
    md.append((core_definition or '_Not found._') + '\n')
    md.append('## Summary\n')
    md.append((summary_body or '_Not found._') + '\n')
    if key_points:
        md.append('## Key Points\n')
        for kp in key_points:
            md.append('- ' + str(kp))
        md.append('')
    md_text = '\n'.join(md)
    with open(output_file, 'w') as f:
        f.write(md_text)
    log.append('Wrote markdown to ' + output_file)

    summary = call_llm(
        system='You are a research summarizer. Write a detailed SUMMARY (100-2000 words) tracing what was searched, which page was opened, what was extracted, and how the markdown was produced.',
        messages=[{'role': 'user', 'content': 'Task: ' + query + '\nLog:\n' + '\n'.join(log) + '\n\nPage: ' + page_url + '\nCore definition: ' + core_definition + '\nMarkdown file: ' + output_file}],
        max_tokens=2000,
    )

    answer = 'Extracted core definition and summary from ' + page_url + ' and saved to ' + output_file + '. Core definition: ' + core_definition[:400]
    return {'answer': answer, 'summary': summary}
