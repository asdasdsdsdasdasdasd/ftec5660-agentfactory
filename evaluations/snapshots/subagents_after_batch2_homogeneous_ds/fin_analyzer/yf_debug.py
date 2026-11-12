import json
from tools import execute_shell_command


def main(query: str) -> dict:
    execute_shell_command("pip install -q yfinance 2>&1 | tail -n 2")
    script = '''
import json
import yfinance as yf

res = {}
try:
    df = yf.download("BTC-USD", period="5y", interval="1d", progress=False, auto_adjust=True)
    res["period_5y_len"] = len(df)
    res["period_5y_head"] = str(df.index[0]) if len(df) else None
    res["period_5y_tail"] = str(df.index[-1]) if len(df) else None
except Exception as e:
    res["period_5y_err"] = str(e)

try:
    t = yf.Ticker("BTC-USD")
    h = t.history(period="5y", interval="1d")
    res["ticker_hist_len"] = len(h)
    res["ticker_hist_head"] = str(h.index[0]) if len(h) else None
    res["ticker_hist_tail"] = str(h.index[-1]) if len(h) else None
except Exception as e:
    res["ticker_hist_err"] = str(e)

# also try a direct chart/data API
import urllib.request
try:
    url = "https://query1.finance.yahoo.com/v8/finance/chart/BTC-USD?range=5y&interval=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    raw = urllib.request.urlopen(req, timeout=20).read().decode()
    d = json.loads(raw)
    ts = d["chart"]["result"][0]["timestamp"]
    res["direct_api_len"] = len(ts)
except Exception as e:
    res["direct_api_err"] = str(e)

print(json.dumps(res, indent=2, default=str))
'''
    with open("yf_probe.py", "w") as f:
        f.write(script)
    out = execute_shell_command("python yf_probe.py 2>&1")
    return {"answer": out, "summary": "Ran yfinance probe: period download vs Ticker.history vs direct Yahoo chart API. Output:\n" + out}
