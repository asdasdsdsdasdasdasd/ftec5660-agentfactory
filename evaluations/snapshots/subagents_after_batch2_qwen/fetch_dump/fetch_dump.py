import re
from llm import call_llm
from tools import read_url_jina


def main(query: str) -> dict:
    # Extract the first URL from the query
    m = re.search(r'https?://[^\s\]\)\}]+', query)
    if not m:
        return {'answer': 'No URL found in query.', 'summary': 'No URL in query: ' + query}
    url = m.group(0)
    try:
        content = read_url_jina(url)
    except Exception as e:
        return {'answer': 'Fetch error: ' + str(e), 'summary': 'Exception: ' + str(e)}
    if isinstance(content, dict):
        if 'error' in content:
            return {'answer': 'Fetch error: ' + str(content['error']), 'summary': 'Error dict: ' + str(content)}
        text = content.get('text', '') or ''
    else:
        text = content or ''
    # Give the LLM the raw text to answer the verification question asked in the query
    answer = call_llm(
        system=(
            "You are given the raw text content of a web page URL. Answer the user's specific question about this page "
            "using ONLY the provided page text. Quote exact phrases/strings from the page when relevant. "
            "If the page text is garbled or does not contain the requested info, say so explicitly."
        ),
        messages=[{'role': 'user', 'content': 'URL: ' + url + '\nQuestion: ' + query + '\n\nPAGE TEXT (first 18000 chars):\n' + text[:18000]}],
        max_tokens=2500,
    )
    summary = call_llm(
        system='Summarize what this fetch-dump produced: the URL, page length, and key findings.',
        messages=[{'role': 'user', 'content': 'URL: ' + url + '\nLength: ' + str(len(text)) + '\nAnswer given: ' + answer[:1000]}],
        max_tokens=600,
    )
    return {'answer': answer, 'summary': 'Fetched ' + url + ' (' + str(len(text)) + ' chars). ' + summary}
