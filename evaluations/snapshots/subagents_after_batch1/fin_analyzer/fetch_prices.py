
import json
import yfinance as yf

ticker = "BTC-USD"
period = "5y"
interval = "1d"
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
