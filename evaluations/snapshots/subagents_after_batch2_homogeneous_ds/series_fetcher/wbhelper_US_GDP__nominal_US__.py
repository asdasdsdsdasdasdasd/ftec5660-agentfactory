import json, urllib.request
url = 'https://api.worldbank.org/v2/country/USA/indicator/NY.GDP.MKTP.CD?format=json&per_page=300&date=2000:2022'
vals = {}
import time
d = None
last_err = ""
for attempt in range(8):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        d = json.loads(urllib.request.urlopen(req, timeout=90).read().decode("utf-8"))
        if isinstance(d, list) and len(d) > 1 and d[1]:
            break
        last_err = str(d)[:100]
    except Exception as e:
        last_err = str(e)
        d = None
    time.sleep(4 + 3 * attempt)
try:
    if isinstance(d, list) and len(d) > 1 and d[1]:
        for rec in d[1]:
            v = rec.get("value"); y = rec.get("date")
            if v is not None and y:
                try:
                    vals[int(y)] = float(v)
                except Exception:
                    pass
except Exception as e:
    vals = {"_error": str(e)}
if not vals:
    vals = {"_error": last_err or "no data returned"}
try:
    json.dump(vals, open('wbout_US_GDP__nominal_US__.json', "w"))
except Exception as we:
    open('wbout_US_GDP__nominal_US__.json', "w").write("{}")
