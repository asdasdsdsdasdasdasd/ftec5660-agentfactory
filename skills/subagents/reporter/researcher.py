import json
import re
from llm import call_llm
from tools import search_serper, read_url_jina


def main(query: str) -> dict:
    plan = call_llm(
        system=(
            "You are a research planning assistant. Given a research task, "
            "produce a JSON object with a key 'queries' containing a list of "
            "4-6 diverse, specific web search queries that together would "
            "surface relevant sources (articles, forum threads, discussions, "
            "reports) about the topic. Also include a key 'focus' describing "
            "what evidence to extract. Return ONLY valid JSON."
        ),
        messages=[{"role": "user", "content": f"Research task: {query}"}],
        max_tokens=800,
    )

    try:
        plan_json = json.loads(re.search(r"\{.*\}", plan, re.DOTALL).group(0))
    except Exception:
        plan_json = {"queries": [query], "focus": query}

    queries = plan_json.get("queries", [query])
    focus = plan_json.get("focus", query)

    seen = set()
    candidates = []
    search_log = []
    for q in queries:
        try:
            results = search_serper(q, topk=8)
        except Exception as e:
            search_log.append(f"Query '{q}' failed: {e}")
            continue
        if results and "error" in results[0]:
            search_log.append(f"Query '{q}' error: {results[0]['error']}")
            continue
        n_new = 0
        for r in results:
            link = r.get("link")
            if link and link not in seen:
                seen.add(link)
                candidates.append(r)
                n_new += 1
        search_log.append(f"Query '{q}' -> {len(results)} results, {n_new} new")

    documents = []
    for r in candidates[:15]:
        url = r.get("link")
        title = r.get("title", "")
        snippet = r.get("snippet", "")
        if not url:
            continue
        try:
            content = read_url_jina(url)
        except Exception as e:
            content = {"error": str(e)}
        if isinstance(content, dict) and "error" in content:
            documents.append({"url": url, "title": title, "snippet": snippet, "content": snippet, "fetch_error": content.get("error")})
            continue
        text = content if isinstance(content, str) else content.get("text", "")
        text = text or ""
        documents.append({"url": url, "title": title, "snippet": snippet, "content": text[:6000]})

    def _parse_json_obj(text):
        t = text.strip()
        t = re.sub(r"^```(?:json)?", "", t).strip()
        t = re.sub(r"```$", "", t).strip()
        # try full parse
        try:
            return json.loads(t)
        except Exception:
            pass
        # try bracket extraction (non-greedy to first closing brace)
        m = re.search(r"\{.*\}", t, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
        return None

    # Extract evidence PER DOCUMENT to avoid truncation of one giant JSON
    all_evidence = []
    doc_summaries = []
    for i, d in enumerate(documents):
        if not d.get("content"):
            continue
        per = call_llm(
            system=(
                "You extract evidence from ONE web document. Return ONLY a JSON "
                "object with keys: 'relevant' (true/false), 'summary' (1-2 sentence "
                "summary of what the doc says about the focus), and 'evidence' "
                "(a list of up to 4 objects, each with 'text' = a short verbatim or "
                "near-verbatim passage relevant to the focus, 'date_hint' = any date/"
                "time reference or empty string, 'sentiment_hint' = one of positive/"
                "negative/neutral/mixed). Do NOT include long text. Keep output compact. "
                "Return ONLY the JSON object, no markdown."
            ),
            messages=[{"role": "user", "content": f"Research focus: {focus}\n\nDocument title: {d['title']}\nDocument URL: {d['url']}\n\nDocument content:\n{d['content'][:5000]}"}],
            max_tokens=1200,
        )
        parsed = _parse_json_obj(per)
        if parsed and isinstance(parsed, dict):
            doc_summaries.append(str(parsed.get("summary", "")))
            evs = parsed.get("evidence", []) or []
            for ev in evs:
                if isinstance(ev, dict) and ev.get("text"):
                    all_evidence.append({
                        "text": str(ev.get("text", ""))[:800],
                        "source": d["url"],
                        "title": d["title"],
                        "date_hint": str(ev.get("date_hint", "")),
                        "sentiment_hint": str(ev.get("sentiment_hint", "")),
                    })

    # Build an overall topic summary from per-doc summaries
    if doc_summaries:
        topic_summary = call_llm(
            system="Summarize the following per-document notes into a coherent 200-400 word overview of what the collected documents say about the research focus.",
            messages=[{"role": "user", "content": f"Focus: {focus}\n\nNotes:\n" + "\n".join(f"- {s}" for s in doc_summaries if s)}],
            max_tokens=900,
        )
    else:
        topic_summary = ""

    extracted = {"evidence": all_evidence, "topic_summary": topic_summary}

    result = {
        "query": query,
        "focus": focus,
        "search_log": search_log,
        "num_documents": len(documents),
        "documents": [{"url": d["url"], "title": d["title"]} for d in documents],
        "evidence": extracted.get("evidence", []),
        "topic_summary": extracted.get("topic_summary", ""),
    }

    with open("evidence.json", "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    summary = call_llm(
        system="You are a research summarizer. Write a detailed SUMMARY (100-2000 words) tracing what was searched, what was found, and the key evidence collected.",
        messages=[{"role": "user", "content": f"Research task: {query}\nSearch log: {search_log}\nDocuments fetched: {len(documents)}\nTopic summary: {result['topic_summary']}\nEvidence items: {len(result['evidence'])}\n\nWrite the SUMMARY."}],
        max_tokens=2000,
    )

    return {
        "answer": f"Collected {len(result['evidence'])} evidence items from {len(documents)} documents. Topic summary: {result['topic_summary'][:400]}",
        "summary": summary,
    }
