import json, re, os
from llm import call_llm
from tools import search_serper, execute_shell_command


def _clean_json(text):
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return {}


def main(query: str) -> dict:
    evidence = []

    # Step 1: LLM parses the query into an asset identification + timeframe + plotting intent.
    plan_txt = call_llm(
        system=(
            "You are a financial data planning assistant. Given a request about an asset's price history, "
            "identify: 1) the asset (name and best ticker/crypto symbol), 2) the asset class (stock/crypto/etf/index/forex), "
            "3) the timeframe in years (default 5), 4) whether they want a price chart and/or annualized volatility. "
            "Return ONLY JSON: {\"asset\":\"...\",\"ticker_candidates\":[\"...\"],\"asset_class\":\"...\",\"years\":5,\"want_plot\":true,\"want_vol\":true}"
        ),
        messages=[{"role": "user", "content": f"Request: {query}"}],
        max_tokens=600,
    )
    plan = _clean_json(plan_txt)
    if not plan:
        plan = {"asset": query, "ticker_candidates": [], "asset_class": "unknown", "years": 5, "want_plot": True, "want_vol": True}
    evidence.append(f"Plan: {json.dumps(plan)}")

    # Step 2: Google search to corroborate ticker + find data source (as requested: use Google)
    search_q = call_llm(
        system="Generate a single concise Google search query to find the ticker symbol and price history data source for the asset in the request. Return only the query text.",
        messages=[{"role": "user", "content": f"Request: {query}\nAsset: {plan.get('asset')}"}],
        max_tokens=120,
    ).strip()
    try:
        results = search_serper(search_q, topk=6)
        snippets = []
        for r in results[:6]:
            if 'error' in r:
                snippets.append(f"ERROR: {r['error']}")
                break
            snippets.append(f"{r.get('title','')} | {r.get('link','')} | {r.get('snippet','')}")
        evidence.append(f"Google search '{search_q}' -> " + "\n".join(snippets))
        # Let LLM refine ticker candidates using search results
        refine = call_llm(
            system="Using the search snippets, determine the correct data ticker for fetching daily price history (e.g., yfinance style). For crypto use format like 'ETH-USD'. Return ONLY JSON: {\"ticker\":\"...\",\"source_hint\":\"...\"}",
            messages=[{"role": "user", "content": f"Asset: {plan.get('asset')}\nCandidates: {plan.get('ticker_candidates')}\nSearch results:\n" + "\n".join(snippets)}],
            max_tokens=300,
        )
        refined = _clean_json(refine)
        if refined.get('ticker'):
            plan['ticker_candidates'] = [refined['ticker']] + plan.get('ticker_candidates', [])
            evidence.append(f"Refined ticker: {refined.get('ticker')}")
    except Exception as e:
        evidence.append(f"Search failed: {e}")

    years = int(plan.get('years') or 5)
    days = int(years * 365) + 10
    tickers = [t for t in plan.get('ticker_candidates', []) if t]
    if not tickers:
        tickers = [plan.get('asset', '')]

    # Step 3: Try to fetch the series via multiple strategies using a generated Python helper.
    fetch_code = r'''
import json, sys, time, datetime
def norm_period(days):
    if days >= 3650: return '10y'
    if days >= 1825: return '5y'
    if days >= 1095: return '3y'
    if days >= 730:  return '2y'
    if days >= 365:  return '1y'
    if days >= 180:  return '6mo'
    return '3mo'
def _parse(data):
    res = data['chart']['result'][0]
    ts = res['timestamp']
    closes = res['indicators']['quote'][0]['close']
    dates=[]; vals=[]
    for i,c in zip(ts,closes):
        if c is None: continue
        dates.append(datetime.datetime.utcfromtimestamp(i).strftime('%Y-%m-%d'))
        vals.append(float(c))
    return dates, vals
def fetch(tickers, days):
    out = {}
    period = norm_period(days)
    # strategy A: yfinance
    try:
        import yfinance as yf
        for t in tickers:
            try:
                df = yf.download(t, period=period, interval='1d', progress=False, auto_adjust=True)
                if df is not None and len(df)>0:
                    closes = df['Close'].dropna()
                    if len(closes)>0:
                        out[t] = {'source':'yfinance','dates':[str(d.date()) for d in closes.index],'close':[float(x) for x in closes.values]}
                        return out
            except Exception as e:
                out.setdefault('_yf_errors',[]).append(f"{t}: {e}")
    except Exception as e:
        out['_yf_import'] = str(e)
    # strategy B: Yahoo chart API direct (range param)
    try:
        import urllib.request
        for t in tickers:
            try:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?range={period}&interval=1d"
                req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
                data = json.loads(urllib.request.urlopen(req, timeout=25).read().decode())
                dates, vals = _parse(data)
                if vals:
                    out[t] = {'source':'yahoo_api','dates':dates,'close':vals}
                    return out
            except Exception as e:
                out.setdefault('_api_errors',[]).append(f"{t}: {e}")
    except Exception as e:
        out['_api_import'] = str(e)
    # strategy C: Yahoo chart API direct (explicit period1/period2 epoch)
    try:
        import urllib.request
        now = int(time.time())
        p1 = now - int(days)*86400
        for t in tickers:
            try:
                url = f"https://query2.finance.yahoo.com/v8/finance/chart/{t}?period1={p1}&period2={now}&interval=1d"
                req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
                data = json.loads(urllib.request.urlopen(req, timeout=25).read().decode())
                dates, vals = _parse(data)
                if vals:
                    out[t] = {'source':'yahoo_api2','dates':dates,'close':vals}
                    return out
            except Exception as e:
                out.setdefault('_api2_errors',[]).append(f"{t}: {e}")
    except Exception as e:
        out['_api2_import'] = str(e)
    return out
result_out = fetch(sys.argv[1].split(','), int(sys.argv[2]))
with open('_fetch_result.json','w') as fp:
    json.dump(result_out, fp)
print('FETCH_WROTE_FILE', len(result_out))
'''
    with open('_fetch_helper.py', 'w') as f:
        f.write(fetch_code)

    series = None
    data_ticker = None
    tk_arg = ','.join([t for t in tickers if t]) or plan.get('asset','')
    for attempt in range(2):
        if os.path.exists('_fetch_result.json'):
            try: os.remove('_fetch_result.json')
            except Exception: pass
        res = execute_shell_command(f'python _fetch_helper.py "{tk_arg}" {days} 2>/dev/null')
        evidence.append(f"Fetch attempt {attempt+1}: {res[:400]}")
        fetched = {}
        try:
            with open('_fetch_result.json') as fp:
                fetched = json.load(fp)
        except Exception as e:
            evidence.append(f"Could not read fetch result file: {e}")
        for t, v in fetched.items():
            if isinstance(v, dict) and v.get('close'):
                series = v
                data_ticker = t
                break
        if series:
            break
        # rebuild ticker list from a second LLM refinement if first failed
        alt = call_llm(
            system="The previous tickers failed to fetch price data. Suggest alternative yfinance-style tickers (crypto e.g. 'BTC-USD', stock plain symbol, index '^GSPC'). Return ONLY a comma-separated list of up to 3 tickers.",
            messages=[{"role": "user", "content": f"Asset: {plan.get('asset')} class: {plan.get('asset_class')} tried: {tickers} errors: {json.dumps(fetched)[:500]}"}],
            max_tokens=120,
        )
        newt = [x.strip() for x in re.split(r'[,;\n]', alt) if x.strip() and x.strip() not in tickers]
        if newt:
            tickers = newt
            tk_arg = ','.join(newt)
            evidence.append(f"Retry with tickers: {newt}")
        else:
            break

    if not series:
        summary = call_llm(
            system="You are a financial research summarizer. Report what was attempted and why it failed.",
            messages=[{"role": "user", "content": f"Query: {query}\nEvidence:\n" + "\n".join(evidence) + "\nThe data fetch failed. Write a detailed SUMMARY (100-1500 words) of attempts, searches, and why no data was obtained."}],
            max_tokens=1500,
        )
        return {"answer": "Failed to fetch price data for the requested asset.", "summary": summary}

    # Save series to json
    with open('series_data.json', 'w') as f:
        json.dump({'ticker': data_ticker, 'series': series, 'plan': plan}, f)
    evidence.append(f"Got {len(series['close'])} points for {data_ticker} from {series['source']} ({series['dates'][0]} to {series['dates'][-1]})")

    # Step 4: Compute annualized volatility + plot via a generated script driven by LLM spec.
    spec_txt = call_llm(
        system=(
            "You are a quantitative finance + plotting spec generator. Given an asset and request, produce JSON: "
            "{\"title\":\"...\",\"ylabel\":\"...\",\"trading_days\":252,\"vol_method\":\"log_returns\",\"annotation\":\"short note\"}. "
            "For daily data annualization use sqrt(252) for trading assets (stocks/etf/index), sqrt(365) for crypto 24/7 assets. "
            "Set trading_days to 365 if asset_class is crypto else 252."
        ),
        messages=[{"role": "user", "content": f"Request: {query}\nAsset: {plan.get('asset')} class: {plan.get('asset_class')} ticker: {data_ticker}"}],
        max_tokens=400,
    )
    spec = _clean_json(spec_txt) or {}
    td = int(spec.get('trading_days') or (365 if str(plan.get('asset_class','')).lower().startswith('crypto') else 252))
    annot = spec.get('annotation', '')
    want_plot = plan.get('want_plot', True)
    want_vol = plan.get('want_vol', True)

    plot_code = f'''
import json, math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime

d = json.load(open('series_data.json'))
ser = d['series']
dates = [datetime.strptime(x, '%Y-%m-%d') for x in ser['dates']]
close = np.array(ser['close'])
ticker = d['ticker']
trading_days = {td}

result = {{}}
# annualized volatility from daily log returns
logret = np.diff(np.log(close))
anvol = float(np.std(logret, ddof=1) * math.sqrt(trading_days)) if len(logret) > 1 else 0.0
result['annualized_volatility'] = anvol
result['num_points'] = int(len(close))
result['start'] = ser['dates'][0]
result['end'] = ser['dates'][-1]
result['start_price'] = float(close[0])
result['end_price'] = float(close[-1])

if {want_plot}:
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(dates, close, color='#1f77b4', linewidth=1.2)
    ax.set_title("{spec.get('title', 'Price History')}")
    ax.set_xlabel('Date')
    ax.set_ylabel("{spec.get('ylabel', 'Price (USD)')}")
    ax.grid(True, alpha=0.3)
    ann = "Annualized volatility: {{:.1f}}%".format(anvol*100)
    extra = "{annot}".strip()
    txt = ann + (("  |  " + extra) if extra else "")
    ax.text(0.01, 0.98, txt, transform=ax.transAxes, va='top', ha='left',
            fontsize=11, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7))
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig('price_chart.png', dpi=120)
    result['chart'] = 'price_chart.png'

json.dump(result, open('volatility_result.json','w'))
print(json.dumps(result))
'''
    with open('make_price_chart.py', 'w') as f:
        f.write(plot_code)

    ensure = execute_shell_command("python -c 'import matplotlib,numpy;print(\"libs ok\")' 2>&1 || pip install -q matplotlib numpy 2>&1 | tail -2")
    evidence.append(f"Lib check: {ensure[:300]}")

    run_out = execute_shell_command('python make_price_chart.py')
    evidence.append(f"Plot/vol script output: {run_out[:1000]}")
    result = {}
    try:
        result = json.loads(run_out.strip().split('\n')[-1])
    except Exception:
        pass

    if not result or 'annualized_volatility' not in result:
        # fallback: compute in pure python quickly
        fallback = execute_shell_command(
            "python -c \"import json,math,numpy as np; d=json.load(open('series_data.json')); c=np.array(d['series']['close']); r=np.diff(np.log(c)); print(json.dumps({'annualized_volatility':float(np.std(r,ddof=1)*math.sqrt("+str(td)+")),'num_points':len(c)}))\""
        )
        try:
            result = json.loads(fallback.strip().split('\n')[-1])
            evidence.append(f"Fallback vol: {fallback[:300]}")
        except Exception:
            pass

    chk = execute_shell_command('ls -la price_chart.png 2>&1')
    evidence.append(f"Chart file check: {chk[:200]}")

    answer = (
        f"Fetched {result.get('num_points')} daily price points for {data_ticker} "
        f"({result.get('start','')} to {result.get('end','')}). "
        f"Annualized volatility = {result.get('annualized_volatility',0)*100:.2f}% "
        f"(using sqrt({td}) annualization). "
        f"Price chart saved to price_chart.png. Start price {result.get('start_price')}, end price {result.get('end_price')}."
    )

    summary = call_llm(
        system="You are a financial data research summarizer. Write a detailed SUMMARY of the process and findings.",
        messages=[{"role": "user", "content": f"Query: {query}\nEvidence:\n" + "\n".join(evidence) + f"\nFinal answer: {answer}\nWrite a SUMMARY (150-1500 words) tracing: search used, data source, ticker, date range, number of points, how annualized volatility was computed, chart file. Include the volatility value."}],
        max_tokens=2000,
    )

    return {"answer": answer, "summary": summary}
