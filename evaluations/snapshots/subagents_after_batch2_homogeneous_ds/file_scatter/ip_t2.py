import json, urllib.request
url = 'https://api.worldbank.org/v2/country/USA/indicator/NY.GDP.MKTP.CD?format=json&per_page=200&date=2000:2022'
import time
d = None; err = ""
for a in range(6):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        d = json.loads(urllib.request.urlopen(req, timeout=90).read().decode("utf-8"))
        if isinstance(d, list) and len(d) > 1 and d[1]:
            break
        err = str(d)[:150]
    except Exception as e:
        err = str(e); d = None
    time.sleep(4 + 3*a)
try:
    meta = d[0] if isinstance(d, list) and d else {}
    rows = d[1] if isinstance(d, list) and len(d) > 1 and d[1] else []
    nonzero = [r for r in rows if r.get("value") is not None]
    print("ROWS", len(rows), "NONNULL", len(nonzero), "ERR", err)
    print("SAMPLE", json.dumps([{"date": r.get("date"), "value": r.get("value")} for r in rows[:6]]))
except Exception as e:
    print("FATAL", str(e), err)
