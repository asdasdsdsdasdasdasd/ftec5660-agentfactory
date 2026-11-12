
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
trading_days = 365

result = {}
# annualized volatility from daily log returns
logret = np.diff(np.log(close))
anvol = float(np.std(logret, ddof=1) * math.sqrt(trading_days)) if len(logret) > 1 else 0.0
result['annualized_volatility'] = anvol
result['num_points'] = int(len(close))
result['start'] = ser['dates'][0]
result['end'] = ser['dates'][-1]
result['start_price'] = float(close[0])
result['end_price'] = float(close[-1])

if True:
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(dates, close, color='#1f77b4', linewidth=1.2)
    ax.set_title("Ethereum (ETH-USD) Daily Price Trend & Annualized Volatility (5 Years)")
    ax.set_xlabel('Date')
    ax.set_ylabel("Price (USD)")
    ax.grid(True, alpha=0.3)
    ann = "Annualized volatility: {:.1f}%".format(anvol*100)
    extra = "Annualized vol calculated using sqrt(365) for 24/7 crypto asset".strip()
    txt = ann + (("  |  " + extra) if extra else "")
    ax.text(0.01, 0.98, txt, transform=ax.transAxes, va='top', ha='left',
            fontsize=11, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7))
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig('price_chart.png', dpi=120)
    result['chart'] = 'price_chart.png'

json.dump(result, open('volatility_result.json','w'))
print(json.dumps(result))
