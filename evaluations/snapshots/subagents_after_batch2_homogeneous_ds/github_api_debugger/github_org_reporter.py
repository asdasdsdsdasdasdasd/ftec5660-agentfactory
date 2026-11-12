import json
import re
from llm import call_llm
from tools import execute_shell_command, read_url_jina, search_serper


def _clean_json(text):
    if not text:
        return None
    t = text.strip()
    t = re.sub(r'^```(?:json)?', '', t).strip()
    t = re.sub(r'```$', '', t).strip()
    m = re.search(r'[\{\[].*[\}\]]', t, re.DOTALL)
    if m:
        t = m.group(0)
    try:
        return json.loads(t)
    except Exception:
        return None


def _curl_json(url):
    # Use Python urllib directly (NOT execute_shell_command) because the shell
    # tool truncates stdout at 5000 chars, corrupting large JSON arrays.
    import urllib.request
    req = urllib.request.Request(url, headers={
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'research-agent',
    })
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            raw = r.read().decode('utf-8', 'replace')
    except Exception as e:
        return {'error': str(e)}
    return _clean_json(raw)


def main(query: str) -> dict:
    log = []

    # Step 1: LLM parses the query to identify the GitHub org, what to extract,
    # and the desired output filename.
    plan_raw = call_llm(
        system=(
            "You parse a user request about a GitHub organization. Return ONLY a JSON object with keys: "
            "'org_handle' (the GitHub organization/user handle if it can be inferred; else empty string), "
            "'org_display_name' (human readable name), "
            "'extract' (what to extract, e.g. description and main repositories), "
            "'min_repos' (minimum number of repositories to list, integer, default 5), "
            "'output_file' (a markdown filename ending .md). "
            "Return ONLY valid JSON."
        ),
        messages=[{'role': 'user', 'content': 'Request: ' + query}],
        max_tokens=600,
    )
    plan = _clean_json(plan_raw) or {}
    org = (plan.get('org_handle') or '').strip()
    display = plan.get('org_display_name') or org
    min_repos = plan.get('min_repos') or 5
    output_file = plan.get('output_file') or 'github_org_report.md'
    if not output_file.endswith('.md'):
        output_file += '.md'
    log.append('Planned org=' + org + ' display=' + display + ' min_repos=' + str(min_repos))

    # Step 2: Resolve the org handle via web search if not parsed
    def _resolve_org(candidate_names):
        for cand in candidate_names:
            if not cand:
                continue
            # try GitHub org API to confirm it exists
            d = _curl_json('https://api.github.com/orgs/' + cand)
            if isinstance(d, dict) and d.get('login'):
                return cand, d
            d = _curl_json('https://api.github.com/users/' + cand)
            if isinstance(d, dict) and d.get('login'):
                return cand, d
        return None, None

    handle = None
    org_obj = None
    if org:
        # try the parsed handle and a few reasonable variants
        variants = [org, org.lower(), org.replace(' ', ''), org.replace(' ', '-').lower()]
        handle, org_obj = _resolve_org(variants)
        log.append('Resolved parsed handle: ' + str(handle))

    # If could not resolve, use web search to find the GitHub org page
    if not handle:
        sq = call_llm(
            system="Generate 2 short web search queries to find the official GitHub organization page for the entity in the request. Return ONLY a JSON list of strings.",
            messages=[{'role': 'user', 'content': query}],
            max_tokens=200,
        )
        queries = _clean_json(sq) or [display + ' github organization']
        if not isinstance(queries, list):
            queries = [str(queries)]
        log.append('Search queries to resolve org: ' + str(queries))
        found_handles = []
        for q in queries:
            try:
                res = search_serper(q, topk=8)
            except Exception as e:
                log.append('Search failed: ' + str(e))
                continue
            for r in (res or []):
                link = r.get('link', '') or ''
                m = re.search(r'github\.com/([A-Za-z0-9_.-]+)', link)
                if m:
                    h = m.group(1)
                    if h not in ('features', 'topics', 'sponsors', 'login', 'join', 'about', 'site', 'readme', 'explore', 'pricing'):
                        found_handles.append(h)
        # dedupe preserving order
        seen = set()
        uniq = []
        for h in found_handles:
            if h not in seen:
                seen.add(h)
                uniq.append(h)
        log.append('Candidate handles from search: ' + str(uniq[:8]))
        handle, org_obj = _resolve_org(uniq[:8])
        log.append('Resolved handle from search: ' + str(handle))

    if not handle:
        summary = call_llm(
            system='Write a SUMMARY explaining what was attempted and why the GitHub org could not be resolved.',
            messages=[{'role': 'user', 'content': 'Query: ' + query + '\nLog:\n' + '\n'.join(log)}],
            max_tokens=800,
        )
        return {'answer': 'Could not resolve the GitHub organization for the request.', 'summary': summary}

    # Step 3: Get full organization description via /orgs endpoint
    org_full = _curl_json('https://api.github.com/orgs/' + handle) or org_obj or {}
    description = org_full.get('description') or ''
    if not description:
        # try the users endpoint bio
        u = _curl_json('https://api.github.com/users/' + handle) or {}
        description = u.get('bio') or ''
    log.append('Org description: ' + repr(description[:200]))

    # Step 4: Fetch repositories sorted by stars desc.
    # IMPORTANT: /orgs/{handle}/repos?sort=stars sorts ASCENDING (returns lowest-star
    # repos first), so we use the SEARCH API which reliably honors sort=stars&order=desc.
    repos = []
    search_url = ('https://api.github.com/search/repositories?q=org:' + handle +
                  '+fork:false&sort=stars&order=desc&per_page=100')
    sd = _curl_json(search_url)
    if isinstance(sd, dict) and isinstance(sd.get('items'), list) and sd['items']:
        repos = sd['items']
        log.append('Search API top repos count=' + str(len(repos)))
    if not repos:
        # Fallback: fetch ALL pages of org repos and sort client-side by stars desc
        allrepos = []
        for page in range(1, 30):
            dd = _curl_json('https://api.github.com/orgs/' + handle +
                            '/repos?per_page=100&page=' + str(page))
            if isinstance(dd, list) and dd:
                allrepos.extend(dd)
            else:
                break
        if allrepos:
            allrepos.sort(key=lambda r: (r or {}).get('stargazers_count') or 0, reverse=True)
            repos = allrepos
            log.append('Fallback paged org repos count=' + str(len(repos)))
    if not repos:
        log.append('No repos from API; trying HTML page')
        html = read_url_jina('https://github.com/' + handle + '?tab=repositories')
        if isinstance(html, dict):
            html = html.get('text', '')
        log.append('HTML repos page length: ' + str(len(html or '')))

    # sort repos by stars desc
    def stars(r):
        return r.get('stargazers_count') or 0
    repos = sorted([r for r in repos if isinstance(r, dict)], key=stars, reverse=True)
    repo_records = []
    for r in repos:
        repo_records.append({
            'name': r.get('name'),
            'description': r.get('description') or '',
            'stars': r.get('stargazers_count') or 0,
            'language': r.get('language') or '',
            'url': r.get('html_url') or '',
            'fork': bool(r.get('fork')),
        })
    log.append('Total repo records: ' + str(len(repo_records)))

    # Step 5: LLM selects/justifies the main repositories (non-fork, most notable)
    repo_listing = '\n'.join(
        '[%d] %s | stars=%d | lang=%s | fork=%s | desc=%s' % (
            i, rec['name'], rec['stars'], rec['language'], rec['fork'], rec['description'][:120]
        ) for i, rec in enumerate(repo_records[:80])
    )
    sel_raw = call_llm(
        system=(
            "You are given a GitHub organization's repositories. Select the MAIN/most notable repositories "
            "(prefer original, non-fork, high-star repos that reflect the org's flagship work). "
            "Return ONLY a JSON object: {'selected_indices': [list of ints in the given index space], "
            "'org_description': '<a clean one/two sentence description of the organization based on its name and its repos>' }."
        ),
        messages=[{'role': 'user', 'content': 'Organization handle: ' + handle + '\nProvided description: ' + description +
                   '\nRequest: ' + query + '\nMinimum repos: ' + str(min_repos) +
                   '\n\nRepositories:\n' + repo_listing}],
        max_tokens=1200,
    )
    sel = _clean_json(sel_raw) or {}
    indices = sel.get('selected_indices') or []
    org_description = sel.get('org_description') or description

    selected = []
    for i in indices:
        if isinstance(i, int) and 0 <= i < len(repo_records):
            selected.append(repo_records[i])
    # fallback: take top non-fork repos by stars if selection insufficient
    if len(selected) < min_repos:
        selected = []
        for rec in repo_records:
            if not rec['fork']:
                selected.append(rec)
            if len(selected) >= max(min_repos, 8):
                break
    # dedupe by name
    seen_n = set()
    final_repos = []
    for rec in selected:
        if rec['name'] and rec['name'] not in seen_n:
            seen_n.add(rec['name'])
            final_repos.append(rec)
    log.append('Final selected repos: ' + str([r['name'] for r in final_repos]))

    # Step 6: Write markdown
    md = []
    md.append('# GitHub Organization: ' + (org_full.get('name') or display or handle) + '\n')
    md.append('**Handle:** https://github.com/' + handle + '  ')
    if org_full.get('blog'):
        md.append('**Website/Blog:** ' + str(org_full.get('blog')) + '  ')
    if org_full.get('location'):
        md.append('**Location:** ' + str(org_full.get('location')) + '  ')
    if org_full.get('public_repos') is not None:
        md.append('**Public repositories:** ' + str(org_full.get('public_repos')) + '  ')
    if org_full.get('followers') is not None:
        md.append('**Followers:** ' + str(org_full.get('followers')) + '  ')
    md.append('')
    md.append('## Description\n')
    md.append((org_description or description or '_No description available._') + '\n')
    md.append('## Main Repositories\n')
    for rec in final_repos:
        line = '- **[' + rec['name'] + '](' + (rec['url'] or ('https://github.com/' + handle + '/' + rec['name'])) + ')**'
        if rec['stars']:
            line += ' - stars: ' + str(rec['stars'])
        if rec['language']:
            line += ' - language: ' + rec['language']
        md.append(line)
        if rec['description']:
            md.append('  - ' + rec['description'])
    md.append('')
    md.append('---')
    md.append('_Data source: GitHub REST API (api.github.com)._')
    md_text = '\n'.join(md)
    with open(output_file, 'w') as f:
        f.write(md_text)
    log.append('Wrote markdown to ' + output_file)

    answer = ('Organization: ' + handle + ' (' + (org_full.get('name') or display) + '). '
              'Description: ' + (org_description or description)[:300] + '. '
              'Listed ' + str(len(final_repos)) + ' main repos: ' + ', '.join(r['name'] for r in final_repos) + '. '
              'Saved to ' + output_file + '.')

    summary = call_llm(
        system='You are a research summarizer. Write a detailed SUMMARY (100-2000 words) tracing the steps: query parsing, org resolution, API fetches, repo selection, and markdown output. Include concrete evidence (description, repo names, stars).',
        messages=[{'role': 'user', 'content': 'Request: ' + query + '\nLog:\n' + '\n'.join(log) +
                   '\n\nOrg description: ' + (org_description or description) +
                   '\nFinal repos: ' + json.dumps(final_repos, indent=2)[:4000] +
                   '\nMarkdown file: ' + output_file}],
        max_tokens=2500,
    )
    return {'answer': answer, 'summary': summary}
