from llm import call_llm
from tools import execute_shell_command


def main(query: str) -> dict:
    evidence = []
    # query is expected to be a ticker or "ticker: N" description; extract ticker via LLM
    tick = call_llm(
        system="Extract a single Yahoo-Finance-style ticker symbol from the text (e.g. ETH-USD, AAPL, ^GSPC). Return ONLY the ticker.",
        messages=[{"role": "user", "content": query}],
        max_tokens=40,
    ).strip()
    evidence.append(f"Ticker extracted: {tick}")

    code = r'''
import json, sys, time, datetime
t=''' + "'" + tick + "'" + r'''
out={}
print('START')
# yfinance
import yfinance as yf
print('yf version import ok')
df = yf.download(t, period='5y', interval='1d', progress=False, auto_adjust=True)
print('yf len', 0 if df is None else len(df))
if df is not None and len(df)>0:
    c=df['Close'].dropna()
    print('yf close len', len(c), 'first', c.index[0], 'last', c.index[-1])
# yahoo api
import urllib.request
url=f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?range=5y&interval=1d"
req=urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
d=json.loads(urllib.request.urlopen(req,timeout=25).read().decode())
r=d['chart']['result'][0]
ts=r['timestamp']; cl=r['indicators']['quote'][0]['close']
v=[x for x in cl if x is not None]
print('api points', len(v), 'first ts', datetime.datetime.utcfromtimestamp(ts[0]).strftime('%Y-%m-%d'), 'last', datetime.datetime.utcfromtimestamp(ts[-1]).strftime('%Y-%m-%d'))
print('DONE')
'''
    import os
    with open('_dbg_fetch.py','w') as f:
        f.write(code)
    out = execute_shell_command('python _dbg_fetch.py 2>&1')
    evidence.append('RAW OUTPUT:\n' + out[:3000])

    summary = call_llm(
        system='You are a debugging assistant. Report exactly what the raw output shows: did yfinance/yahoo API return data, how many points, date range, and any errors.',
        messages=[{"role": "user", "content": 'Evidence:\n' + '\n'.join(evidence) + '\nWrite a clear diagnostic SUMMARY (100-800 words).'}],
        max_tokens=1200,
    )
    return {"answer": out[:1500], "summary": summary}
