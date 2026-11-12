
import json, sys, time, datetime
t='AAPL'
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
