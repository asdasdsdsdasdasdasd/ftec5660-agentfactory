
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
