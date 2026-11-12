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
    # 1) Plan the org slug + output file + how many repos
    plan_raw = call_llm(
        system=(
            "You are a research planner. From the task, output ONLY JSON with keys: "
            "'org_slug' (GitHub org login, e.g. facebookresearch; if a github URL is in the task, extract its first path segment), "
            "'num_repos' (min repos to list, default 5), 'output_file' (markdown filename ending .md). Return ONLY valid JSON."
        ),
        messages=[{'role': 'user', 'content': 'Task: ' + query}],
        max_tokens=300,
    )
    plan = _clean_json(plan_raw) or {}
    slug = (plan.get('org_slug') or '').strip()
    num_repos = plan.get('num_repos') or 5
    output_file = plan.get('output_file') or 'github_org_report.md'
    if not output_file.endswith('.md'):
        output_file += '.md'

    # Try to resolve slug via search if not present / suspicious
    if not slug or ' ' in slug:
        try:
            res = search_serper('github organization ' + query, topk=6)
            for r in res:
                mm = re.match(r'https?://github\.com/([^/?#]+)', r.get('link', ''))
                if mm and mm.group(1).lower() not in ('orgs', 'login', 'about', 'features', 'topics'):
                    slug = mm.group(1)
                    log.append('Resolved slug via search: ' + slug)
                    break
        except Exception as e:
            log.append('search err ' + str(e))
    log.append('slug=' + slug + ' num_repos=' + str(num_repos) + ' output_file=' + output_file)

    if not slug:
        return {'answer': 'Could not resolve org slug.', 'summary': 'No slug resolved for: ' + query}

    # 2) Fetch org meta -> file -> compact
    execute_shell_command('curl -s -H "Accept: application/vnd.github+json" https://api.github.com/orgs/' + slug + ' -o _org2.json')
    org_c = execute_shell_command("python3 -c \"import json;d=json.load(open('_org2.json'));print(json.dumps({k:d.get(k) for k in ['login','name','description','location','blog','public_repos']}))\"")
    org = {}
    try:
        org = json.loads(org_c)
    except Exception as e:
        log.append('org parse fail ' + str(e))

    # 3) Fetch repos -> file -> compact top N
    execute_shell_command('curl -s -H "Accept: application/vnd.github+json" "https://api.github.com/orgs/' + slug + '/repos?per_page=100" -o _repos2.json')
    py = ("python3 -c \"import json;"
          "d=json.load(open('_repos2.json'));"
          "d=d if isinstance(d,list) else [];"
          "d.sort(key=lambda r:r.get('stargazers_count',0),reverse=True);"
          "print(json.dumps([{'name':r.get('name'),'description':(r.get('description') or '')[:180],'stars':r.get('stargazers_count',0),'url':r.get('html_url','')} for r in d[:20]]))\"")
    repos_c = execute_shell_command(py)
    repos = []
    try:
        repos = json.loads(repos_c)
    except Exception as e:
        log.append('repos parse fail ' + str(e))
    top = repos[:max(int(num_repos), 5)] if isinstance(repos, list) else []
    log.append('org name=' + str(org.get('name')) + ' desc=' + repr(org.get('description')) + ' public_repos=' + str(org.get('public_repos')))
    log.append('top repos=' + str([t.get('name') for t in top]))

    # 4) Description text (factual, no fabrication)
    desc_real = org.get('description') or ''
    desc_text = call_llm(
        system=(
            "Write 2-4 sentence factual description of this GitHub organization. Use ONLY the verified metadata below. "
            "If 'github_description' is empty, state that the org has no formal bio set on GitHub, then describe it from verified facts "
            "(name, location, website, public repo count, and the nature of its top repositories). Do NOT invent claims."
        ),
        messages=[{'role': 'user', 'content': 'Verified: name=' + str(org.get('name')) + '; login=' + str(org.get('login')) + '; location=' + str(org.get('location')) + '; website=' + str(org.get('blog')) + '; public_repos=' + str(org.get('public_repos')) + '; github_description=' + (repr(desc_real) if desc_real else 'EMPTY') + '\nTop repos: ' + json.dumps([{'name': t.get('name'), 'description': t.get('description')} for t in top])[:1500]}],
        max_tokens=400,
    )

    # 5) Build ONE clean markdown doc in Python (explicit truncate + verify)
    lines = []
    lines.append('# ' + (org.get('name') or slug) + ' (GitHub Organization)')
    lines.append('')
    lines.append('**GitHub URL:** https://github.com/' + slug)
    if org.get('blog'):
        lines.append('**Website:** ' + str(org.get('blog')))
    if org.get('location'):
        lines.append('**Location:** ' + str(org.get('location')))
    if org.get('public_repos') is not None:
        lines.append('**Public repositories:** ' + str(org.get('public_repos')))
    lines.append('')
    lines.append('## Description')
    lines.append('')
    lines.append(desc_text.strip())
    lines.append('')
    lines.append('## Main Repositories')
    lines.append('')
    lines.append('| Repository | Description | Stars |')
    lines.append('| --- | --- | --- |')
    for t in top:
        nm = str(t.get('name', ''))
        ds = str(t.get('description', '')).replace('|', '\\|')
        lines.append('| [' + nm + '](' + str(t.get('url', '')) + ') | ' + ds + ' | ' + str(t.get('stars', '')) + ' |')
    md = '\n'.join(lines) + '\n'

    # Write via python to guarantee clean overwrite
    import pathlib
    pathlib.Path(output_file).write_text(md, encoding='utf-8')

    # 6) Verify: count headers & sections & rows via shell
    verify = execute_shell_command("printf 'TITLES=%s\\n' \"$(grep -c '^# ' " + output_file + ")\"; printf 'DESC=%s\\n' \"$(grep -c '^## Description' " + output_file + ")\"; printf 'MAIN=%s\\n' \"$(grep -c '^## Main Repositories' " + output_file + ")\"; printf 'FENCE=%s\\n' \"$(grep -c '```' " + output_file + ")\"; printf 'LINES=%s\\n' \"$(wc -l < " + output_file + ")\"")
    log.append('VERIFY: ' + verify.replace('\n', ' '))

    summary = call_llm(
        system='Write a SUMMARY (100-1500 words) of how the GitHub org data was extracted: slug, API metadata (name/description/public_repos), top repos by stars, and confirmation the markdown was written cleanly (single title/description/repos section). Include the VERIFY numbers.',
        messages=[{'role': 'user', 'content': 'Task: ' + query + '\nLog:\n' + '\n'.join(log) + '\nTop repos+stars: ' + json.dumps([{'n': t.get('name'), 's': t.get('stars')} for t in top]) + '\nOutput: ' + output_file}],
        max_tokens=1800,
    )
    answer = 'Org ' + slug + ' (' + str(org.get('name')) + '). Description field: ' + (repr(desc_real) if desc_real else 'EMPTY') + '. Top ' + str(len(top)) + ' repos: ' + ', '.join([str(t.get('name')) for t in top]) + '. Wrote clean ' + output_file + '. Verify: ' + verify.replace('\n', ' ')
    return {'answer': answer, 'summary': summary}
