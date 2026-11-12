import json
import re
from datetime import datetime

from llm import call_llm
from tools import execute_shell_command


def _ensure_deps():
    execute_shell_command("pip install -q yfinance pandas matplotlib requests 2>&1 | tail -n 3")


def _fetch_data(spec):
    ticker = spec.get("ticker") or spec.get("symbol")
    period = spec.get("period") or "1y"
    interval = spec.get("interval") or "1d"
    fetch_script = '''
import json
import yfinance as yf

ticker = %s
period = %s
interval = %s
try:
    df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
    if df is None or len(df) == 0:
        print(json.dumps({"error": "no_data", "ticker": ticker}))
    else:
        if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
            df.columns = [c[0] for c in df.columns]
        df = df.reset_index()
        date_col = None
        for c in df.columns:
            if str(c).lower() in ("date", "datetime", "index"):
                date_col = c
                break
        if date_col is None:
            date_col = df.columns[0]
        close_col = "Close" if "Close" in df.columns else df.columns[-1]
        records = []
        for _, row in df.iterrows():
            try:
                records.append({"date": str(row[date_col])[:10], "close": float(row[close_col])})
            except Exception:
                continue
        with open("raw_records.json", "w") as rf:
            json.dump({"ticker": ticker, "records": records}, rf)
        print(json.dumps({"ticker": ticker, "count": len(records), "saved": "raw_records.json"}))
except Exception as e:
    print(json.dumps({"error": str(e), "ticker": ticker}))
''' % (json.dumps(ticker), json.dumps(period), json.dumps(interval))
    with open("fetch_prices.py", "w") as f:
        f.write(fetch_script)
    out = execute_shell_command("python fetch_prices.py")
    data = None
    # Primary: read records from the file written by the fetch script
    try:
        with open("raw_records.json", "r") as rf:
            data = json.load(rf)
    except Exception:
        data = None
    # Fallback: parse stdout JSON lines
    if not data or not data.get("records"):
        for line in reversed(out.strip().splitlines()):
            line = line.strip()
            if line.startswith("{"):
                try:
                    cand = json.loads(line)
                    if cand.get("records"):
                        data = cand
                        break
                except Exception:
                    continue
    return data, out


def _compute_stats(records, spec):
    import math
    closes = [r["close"] for r in records if r.get("close")]
    dates = [r["date"] for r in records if r.get("close")]
    if len(closes) < 2:
        return {"error": "insufficient data"}
    log_returns = []
    for i in range(1, len(closes)):
        if closes[i - 1] > 0 and closes[i] > 0:
            log_returns.append(math.log(closes[i] / closes[i - 1]))
    n = len(log_returns)
    mean_lr = sum(log_returns) / n
    var = sum((x - mean_lr) ** 2 for x in log_returns) / (n - 1) if n > 1 else 0.0
    std_daily = math.sqrt(var)
    interval = (spec.get("interval") or "1d").lower()
    ann_factor = 365
    if interval.endswith("wk"):
        ann_factor = 52
    elif interval.endswith("mo"):
        ann_factor = 12
    elif interval.endswith("h") or "hour" in interval:
        ann_factor = 365 * 24
    annualized_vol = std_daily * math.sqrt(ann_factor) * 100
    start_price = closes[0]
    end_price = closes[-1]
    total_return = (end_price / start_price - 1) * 100 if start_price else None
    return {
        "num_points": len(closes),
        "start_date": dates[0],
        "end_date": dates[-1],
        "start_price": start_price,
        "end_price": end_price,
        "total_return_pct": total_return,
        "daily_std": std_daily,
        "annualization_factor": ann_factor,
        "annualized_volatility_pct": annualized_vol,
    }


def main(query: str) -> dict:
    _ensure_deps()

    plan_raw = call_llm(
        system=(
            "You are a financial data planner. Given a user query, extract as strict JSON: "
            "{asset_name, ticker, period, interval, chart_type, chart_title, x_label, y_label, statistic}. "
            "ticker = Yahoo Finance symbol (BTC-USD Bitcoin, ETH-USD Ethereum, AAPL, ^GSPC S&P500). "
            "period = yfinance period string like '1y','5y','max','6mo'; if query says 'past N years' use '<N>y'. "
            "interval = '1d' default, '1wk','1mo','1h'. chart_type='line' unless specified. "
            "Return ONLY JSON, no markdown."
        ),
        messages=[{"role": "user", "content": query}],
        max_tokens=500,
    )
    spec = {}
    m = re.search(r"\{.*\}", plan_raw, re.DOTALL)
    if m:
        try:
            spec = json.loads(m.group(0))
        except Exception:
            spec = {}
    if not spec.get("ticker"):
        spec["ticker"] = "BTC-USD"
    if not spec.get("period"):
        spec["period"] = "5y"
    if not spec.get("interval"):
        spec["interval"] = "1d"
    spec.setdefault("chart_title", (spec.get("ticker") or "Asset") + " Price Trend")

    data, raw_out = _fetch_data(spec)
    if not data or "error" in data or not data.get("records"):
        summary = call_llm(
            system="You summarize a data-fetch failure concisely for a meta-agent.",
            messages=[{"role": "user", "content": "Query: " + query + "\nSpec: " + json.dumps(spec) + "\nRaw: " + str(raw_out)[:1500] + "\nWhat went wrong?"}],
            max_tokens=300,
        )
        return {"answer": "FAILED to fetch price data", "summary": summary}

    records = data["records"]
    stats = _compute_stats(records, spec)

    with open("price_data.json", "w") as f:
        json.dump({"spec": spec, "records": records, "stats": stats}, f)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    xs = [datetime.strptime(r["date"], "%Y-%m-%d") for r in records if r.get("close")]
    ys = [r["close"] for r in records if r.get("close")]
    plt.figure(figsize=(12, 6))
    plt.plot(xs, ys, color="#f2a900", linewidth=1.2)
    plt.title(spec.get("chart_title", "Price Trend"))
    plt.xlabel(spec.get("x_label", "Date"))
    plt.ylabel(spec.get("y_label", "Price (USD)"))
    plt.grid(True, alpha=0.3)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    plt.gcf().autofmt_xdate()
    chart_path = "price_chart.png"
    plt.tight_layout()
    plt.savefig(chart_path, dpi=120)
    plt.close()

    av = stats.get("annualized_volatility_pct")
    tr = stats.get("total_return_pct")
    answer = (
        (spec.get("asset_name") or spec["ticker"]) + " price trend chart saved to " + chart_path + ". "
        "Data range " + str(stats.get("start_date")) + " to " + str(stats.get("end_date")) + " (" + str(stats.get("num_points")) + " points). "
        "Annualized volatility = " + ("%.2f%%" % av if av is not None else "NA") + " "
        "(daily log-return std " + str(round(stats.get("daily_std", 0), 5)) + " x sqrt(" + str(stats.get("annualization_factor")) + ")). "
        "Total return over period = " + ("%.2f%%" % tr if tr is not None else "NA") + " "
        "from " + str(round(stats.get("start_price", 0), 2)) + " to " + str(round(stats.get("end_price", 0), 2)) + "."
    )

    summary = call_llm(
        system="You are a research summarizer. Write a detailed SUMMARY of the data-analysis process and findings.",
        messages=[{"role": "user", "content": (
            "Query: " + query + "\nParsed spec: " + json.dumps(spec) + "\nStats: " + json.dumps(stats) + "\nAnswer: " + answer +
            "\n\nWrite a SUMMARY (100-500 words) tracing: how asset/ticker/period were parsed, how data was fetched, the statistical method (std of daily log returns x sqrt of annualization factor) and the numeric results."
        )}],
        max_tokens=1200,
    )

    return {"answer": answer, "summary": summary}
