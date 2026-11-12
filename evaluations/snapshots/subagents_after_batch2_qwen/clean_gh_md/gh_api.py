import json
import re
from llm import call_llm
from tools import execute_shell_command, search_serper


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


def main(query: str) -> dict:
    log = []
    # 1) Plan: figure out the GitHub org slug (and optional extra info) from the task
    plan_raw = call_llm(
        system=(
            "You are a research planner for tasks that require finding an organization's GitHub presence. "
            "Given a task, output ONLY JSON with keys: 'org_slug' (the GitHub organization login/slug, e.g. facebookresearch), "
            "'org_name_hint' (human name), 'num_repos' (how many main repos to list, default 5), "
            "'output_file' (markdown filename ending .md), 'task_summary' (one line). "
            "If you are unsure of the exact slug, output your best guess. Return ONLY valid JSON."
        ),
        messages=[{'role': 'user', 'content': 'Task: ' + query}],
        max_tokens=400,
    )
    plan = _clean_json(plan_raw) or {}
    slug = (plan.get('org_slug') or '').strip()
    num_repos = plan.get('num_repos') or 5
    output_file = plan.get('output_file') or 'github_org_report.md'
    if not output_file.endswith('.md'):
        output_file += '.md'
    log.append('Planned slug=' + slug + ' num_repos=' + str(num_repos))

    # 2) Try to confirm slug via search if empty or to validate
    try:
        results = search_serper(('github.com/' + slug + ' organization') if slug else 'GitHub organization', topk=6)
        for r in results:
            link = r.get('link', '')
            mm = re.match(r'https?://github\.com/([^/?#]+)', link)
            if mm:
                cand = mm.group(1)
                if cand.lower() not in ('orgs', 'login', 'about', 'features', 'topics'):
                    if not slug:
                        slug = cand
                        log.append('Resolved slug from search: ' + slug)
                        break
    except Exception as e:
        log.append('Search err: ' + str(e))

    if not slug:
        summary = call_llm(system='Explain failure.', messages=[{'role': 'user', 'content': 'Task: ' + query + '\nLog:\n' + '\n'.join(log)}], max_tokens=400)
        return {'answer': 'Could not resolve a GitHub org slug.', 'summary': summary}

    # 3) Fetch org metadata via API (curl to file to avoid stdout 5000-char truncation)
    execute_shell_command('curl -s -H "Accept: application/vnd.github+json" https://api.github.com/orgs/' + slug + ' -o _org.json')
    org_compact = execute_shell_command("python3 -c \"import json;d=json.load(open('_org.json'));print(json.dumps({k:d.get(k) for k in ['login','name','description','location','blog','public_repos']}))\"")
    org = None
    try:
        org = json.loads(org_compact)
    except Exception:
        log.append('Org JSON parse failed: ' + str(org_compact)[:200])
    if org and isinstance(org, dict) and org.get('login'):
        slug = org.get('login', slug)
        log.append('Org API OK: name=' + str(org.get('name')) + ' desc=' + repr(org.get('description')) + ' public_repos=' + str(org.get('public_repos')))
    else:
        log.append('Org API not usable: ' + str(org_json)[:200])

    # 4) Fetch repos sorted by stars -> file, then parse & compact top N via python
    execute_shell_command('curl -s -H "Accept: application/vnd.github+json" "https://api.github.com/orgs/' + slug + '/repos?per_page=100&type=public" -o _repos.json')
    py_cmd = (
        "python3 -c \"import json;"
        "d=json.load(open('_repos.json'));"
        "d = d if isinstance(d,list) else [];"
        "d.sort(key=lambda r: r.get('stargazers_count',0), reverse=True);"
        "out=[{'name':r.get('name'),'description':(r.get('description') or '')[:200],'stars':r.get('stargazers_count',0),'url':r.get('html_url',''),'language':r.get('language') or ''} for r in d[:20]];"
        "print(json.dumps(out))\""
    )
    repos_compact = execute_shell_command(py_cmd)
    repos = []
    try:
        data = json.loads(repos_compact)
        if isinstance(data, list):
            repos = data
            log.append('Repos API OK: ' + str(len(repos)) + ' repos parsed')
    except Exception as e:
        log.append('Repos parse failed: ' + str(e) + ' | out=' + str(repos_compact)[:200])

    top = repos[:max(int(num_repos), 5)] if repos else []

    # 5) Compose description. Use real org metadata. If description empty, synthesize a FACTUAL summary
    #    strictly from verified metadata (name, location, blog, public_repos count) and note bio absent.
    org_real_desc = ''
    if org and isinstance(org, dict):
        org_real_desc = org.get('description') or ''
    verified_meta = ''
    if org and isinstance(org, dict):
        verified_meta = (
            'name=' + str(org.get('name')) +
            '; login=' + str(org.get('login')) +
            '; location=' + str(org.get('location')) +
            '; blog=' + str(org.get('blog')) +
            '; public_repos=' + str(org.get('public_repos')) +
            '; github_description=' + (repr(org_real_desc) if org_real_desc else 'EMPTY (no bio set)')
        )
    desc_llm = call_llm(
        system=(
            "Write a concise, FACTUAL description (2-5 sentences) of this GitHub organization for a report. "
            "Base it ONLY on the verified metadata and the top repositories provided. Do NOT invent a bio. "
            "If the GitHub 'description' field is empty, say the organization does not publish a formal bio on GitHub, "
            "then describe it using the verified facts (name, location, website, number of public repositories, and the nature of its top repos)."
        ),
        messages=[{'role': 'user', 'content': 'Task: ' + query + '\nVerified metadata: ' + verified_meta + '\nTop repos: ' + json.dumps([{'name': t['name'], 'description': t['description']} for t in top])[:2000]}],
        max_tokens=500,
    )

    # 6) Write markdown
    md = []
    md.append('# ' + (org.get('name') if org and isinstance(org, dict) and org.get('name') else slug) + ' (GitHub Organization)\n')
    md.append('**GitHub URL:** https://github.com/' + slug + '\n')
    if org and isinstance(org, dict):
        if org.get('blog'):
            md.append('**Website:** ' + str(org.get('blog')) + '\n')
        if org.get('location'):
            md.append('**Location:** ' + str(org.get('location')) + '\n')
        if org.get('public_repos') is not None:
            md.append('**Public repositories:** ' + str(org.get('public_repos')) + '\n')
    md.append('## Description\n')
    md.append((desc_llm or '_Not found._') + '\n')
    md.append('## Main Repositories\n')
    if top:
        md.append('| Repository | Description | Stars |')
        md.append('| --- | --- | --- |')
        for t in top:
            ds = (t['description'] or '').replace('|', '\\|')
            md.append('| [' + str(t['name']) + '](' + str(t['url']) + ') | ' + ds + ' | ' + str(t['stars']) + ' |')
        md.append('')
    else:
        md.append('_No repositories retrieved._\n')
    md_text = '\n'.join(md)
    with open(output_file, 'w') as f:
        f.write(md_text)
    log.append('Wrote ' + output_file + ' with ' + str(len(top)) + ' repos')

    summary = call_llm(
        system='Write a detailed SUMMARY (100-2000 words) tracing: how the org slug was determined, what the GitHub API returned (name, description field, public_repos), what the top repos are by stars, and how the markdown was written. Include exact evidence values.',
        messages=[{'role': 'user', 'content': 'Task: ' + query + '\nLog:\n' + '\n'.join(log) + '\n\nOrg meta: ' + verified_meta + '\nTop repo names+stars: ' + json.dumps([{'n': t['name'], 's': t['stars']} for t in top]) + '\nOutput file: ' + output_file}],
        max_tokens=2000,
    )
    answer = 'GitHub org resolved to ' + slug + '. Description field: ' + (repr(org_real_desc) if org_real_desc else 'EMPTY') + '. Listed top ' + str(len(top)) + ' repos by stars: ' + ', '.join([t['name'] for t in top]) + '. Saved to ' + output_file + '.'
    return {'answer': answer, 'summary': summary}
