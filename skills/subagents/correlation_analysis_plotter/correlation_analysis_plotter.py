import json, os
from llm import call_llm
from tools import execute_shell_command

NL = chr(10)


def main(query: str) -> dict:
    log = []
    # 1) find candidate JSON data files
    ls = execute_shell_command("ls -1 *.json 2>/dev/null")
    log.append("json files: " + str(ls)[:400])

    # 2) LLM decides which file + which two variables + whether to log-transform x
    plan_raw = call_llm(
        system=(
            "You are a statistical analysis planner. The user wants a correlation analysis between "
            "two numeric variables stored in a JSON data file. Inspect the request and choose: the data "
            "file, the numeric x-field and y-field (exact key substrings as they appear in records), "
            "whether x should be log10-transformed (true for money/income/GDP/population-like variables "
            "that span orders of magnitude), title, axis labels. Output ONLY valid JSON with keys: "
            "file, x_field, y_field, log_x (bool), title, x_label, y_label. No markdown.\n"
            "Available json files:\n" + str(ls) + "\nRequest:\n" + query
        ),
        messages=[{"role": "user", "content": query}],
    )
    try:
        plan = json.loads(plan_raw)
    except Exception:
        s = plan_raw.find("{"); e = plan_raw.rfind("}")
        plan = json.loads(plan_raw[s:e + 1]) if s != -1 and e != -1 else {}
        log.append("plan parse fallback used")

    fpath = plan.get("file", "wb_data.json")
    if not os.path.exists(fpath):
        # pick any json with a records list
        for cand in [x.strip() for x in str(ls).split() if x.strip().endswith(".json")]:
            try:
                d = json.load(open(cand))
                if isinstance(d, dict) and isinstance(d.get("records"), list):
                    fpath = cand; break
            except Exception:
                pass
    data = json.load(open(fpath))
    records = data.get("records", data if isinstance(data, list) else [])
    log.append("loaded %s with %d records" % (fpath, len(records)))

    # resolve field keys: exact match, substring both ways, then fuzzy token overlap
    keys = list(records[0].keys()) if records else []
    def resolve(field):
        if not field:
            return None
        if field in keys:
            return field
        fl = field.lower().strip()
        for k in keys:
            if fl in k.lower() or k.lower() in fl:
                return k
        import re as _re
        def toks(s):
            return set(_re.findall(r"[a-z0-9]+", s.lower()))
        ft = toks(field); best = None; best_score = 0
        for k in keys:
            kt = toks(k)
            if not kt: continue
            score = len(ft & kt) / float(len(ft | kt) + 1e-9)
            if score > best_score:
                best_score = score; best = k
        return best if best_score > 0.3 else None
    xk = resolve(plan.get("x_field", "")); yk = resolve(plan.get("y_field", ""))
    if not xk or not yk:
        return {"answer": "Could not resolve fields x=%s y=%s keys=%s" % (plan.get("x_field"), plan.get("y_field"), keys), "summary": "\n".join(log)}

    pts = []
    for r in records:
        x = r.get(xk); y = r.get(yk)
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            pts.append({"label": r.get("country", r.get("name", "")), "x": float(x), "y": float(y)})
    if len(pts) < 3:
        return {"answer": "Not enough numeric points: %d" % len(pts), "summary": "\n".join(log)}

    # write a data bundle + a plotting script that computes BOTH linear(x) and log-x fits
    log_x = bool(plan.get("log_x", True))
    bundle = {"points": pts, "spec": {"title": plan.get("title", "Correlation"), "x_label": plan.get("x_label", xk),
              "y_label": plan.get("y_label", yk), "log_x": log_x, "x_key": xk, "y_key": yk}}
    json.dump(bundle, open("corr_bundle.json", "w"), indent=2)

    script = '''
import json, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
b = json.load(open("corr_bundle.json"))
pts = b["points"]; spec = b["spec"]
xs = np.array([p["x"] for p in pts], float); ys = np.array([p["y"] for p in pts], float)
labels = [p["label"] for p in pts]
stats = {"n": int(len(xs))}
# linear fit in raw space
sl, ic = np.polyfit(xs, ys, 1); yp = sl*xs+ic
ss_res = float(np.sum((ys-yp)**2)); ss_tot = float(np.sum((ys-ys.mean())**2))
stats["lin_slope"]=float(sl); stats["lin_intercept"]=float(ic)
stats["lin_r2"]=1-ss_res/ss_tot if ss_tot>0 else 0; stats["lin_r"]=float(np.corrcoef(xs,ys)[0,1])
# log-x fit (Preston-style): y = a*log10(x)+b
lx = np.log10(np.clip(xs, 1e-9, None))
sl2, ic2 = np.polyfit(lx, ys, 1); yp2 = sl2*lx+ic2
ssr2 = float(np.sum((ys-yp2)**2))
stats["log_slope"]=float(sl2); stats["log_intercept"]=float(ic2)
stats["log_r2"]=1-ssr2/ss_tot if ss_tot>0 else 0; stats["log_r"]=float(np.corrcoef(lx,ys)[0,1])

fig, ax = plt.subplots(figsize=(11,7))
ax.scatter(xs, ys, s=80, color="#1f77b4", edgecolors="black", zorder=3, label="Countries")
for x,y,lb in zip(xs,ys,labels):
    ax.annotate(lb,(x,y),textcoords="offset points",xytext=(6,5),fontsize=8,color="#333")
if spec.get("log_x"):
    xg = np.linspace(lx.min(), lx.max(), 200)
    ax.plot(10**xg, sl2*xg+ic2, color="#d62728", lw=2.5, zorder=2, label="Log-linear fit")
    box = ("y = {:.3f}*log10(x) + {:.2f}".format(sl2, ic2) + chr(10) +
           "R^2 = {:.3f}   r = {:.3f}".format(stats["log_r2"], stats["log_r"]) + chr(10) +
           "(linear R^2 = {:.3f})".format(stats["lin_r2"]) + chr(10) + "n = {}".format(len(xs)))
else:
    xg = np.linspace(xs.min(), xs.max(), 200)
    ax.plot(xg, sl*xg+ic, color="#d62728", lw=2.5, zorder=2, label="Linear fit")
    box = ("y = {:.6g}*x + {:.4g}".format(sl, ic) + chr(10) +
           "R^2 = {:.3f}   r = {:.3f}".format(stats["lin_r2"], stats["lin_r"]) + chr(10) + "n = {}".format(len(xs)))
ax.text(0.03,0.97,box,transform=ax.transAxes,fontsize=10,va="top",ha="left",
        bbox=dict(boxstyle="round",facecolor="white",alpha=0.9,edgecolor="gray"))
ax.set_title(spec["title"], fontsize=14, fontweight="bold")
ax.set_xlabel(spec["x_label"], fontsize=11); ax.set_ylabel(spec["y_label"], fontsize=11)
if spec.get("log_x"): ax.set_xscale("log")
ax.grid(True, which="both", alpha=0.3); ax.legend(loc="lower right")
fig.tight_layout(); fig.savefig("correlation_scatter.png", dpi=140)
json.dump(stats, open("corr_stats.json","w"), indent=2)
print(json.dumps(stats))
'''
    open("make_corr.py","w").write(script)
    out = execute_shell_command("python make_corr.py 2>&1")
    log.append("plot run: " + str(out)[:800])
    stats = {}
    if os.path.exists("corr_stats.json"):
        stats = json.load(open("corr_stats.json"))
    png_ok = os.path.exists("correlation_scatter.png")

    # LLM writes the interpretation + builds a markdown report
    interp = call_llm(
        system=(
            "You are a data analyst specializing in the economics of health (the Preston curve). "
            "Given correlation statistics between an economic indicator and a health outcome, write a "
            "rigorous, objective interpretation. Cover: direction and strength of the relationship, "
            "why a log transform of income is the standard approach, the 'diminishing returns' pattern, "
            "notable country outliers, causality caveats (correlation != causation; confounders like "
            "healthcare systems, inequality, lifestyle), and data limitations (single year, current-US$ "
            "GDP affected by exchange rates). Be concise but substantive."
        ),
        messages=[{"role": "user", "content": "Data points (country, GDP, life expectancy): " + json.dumps([(p['label'], p['x'], p['y']) for p in pts]) + "\nStats: " + json.dumps(stats) + "\nSource: " + str(data.get('source','World Bank')) + ", year: " + str(records[0].get('year','')) }],
        max_tokens=1500,
    )

    # write markdown report
    rows = "\n".join(["| %s | %,.0f | %.1f |".replace("%,", "_").replace("_,", ",") % (p['label'], p['x'], p['y']) for p in []])  # placeholder safe
    tbl_lines = ["| Country | %s | %s |" % (xk, yk), "|---|---|---|"]
    for p in pts:
        tbl_lines.append("| %s | %s | %.1f |" % (p['label'], format(p['x'], ',.0f'), p['y']))
    table = "\n".join(tbl_lines)
    report = ("# Economic Development vs Health Outcomes\n\n"
              "Source: " + str(data.get('source','World Bank Open Data')) + " (year " + str(records[0].get('year','')) + ")\n\n"
              "## Data\n\n" + table + "\n\n"
              "## Regression results\n\n"
              "- Log-linear (income in log10): slope = %.3f, intercept = %.2f, R^2 = %.3f, r = %.3f\n" % (stats.get('log_slope',0), stats.get('log_intercept',0), stats.get('log_r2',0), stats.get('log_r',0)) +
              "- Linear (raw income): slope = %.6g, R^2 = %.3f, r = %.3f\n\n" % (stats.get('lin_slope',0), stats.get('lin_r2',0), stats.get('lin_r',0)) +
              "## Interpretation\n\n" + str(interp) + "\n\n"
              "![correlation scatter](correlation_scatter.png)\n")
    open("findings_report.md","w").write(report)

    summary = call_llm(
        system="You are a research summarizer. Write a clear SUMMARY of this correlation analysis pipeline.",
        messages=[{"role":"user","content": "Query: "+query+"\nLog:\n"+NL.join(log)+"\nStats: "+json.dumps(stats)+"\nPNG exists: "+str(png_ok)+"\nWrote findings_report.md"}],
        max_tokens=1200,
    )
    answer = ("Analysis complete. PNG=%s. Log-linear R^2=%.3f r=%.3f; linear R^2=%.3f r=%.3f. "
              "Files: correlation_scatter.png, corr_stats.json, findings_report.md, corr_bundle.json" %
              (png_ok, stats.get('log_r2',0), stats.get('log_r',0), stats.get('lin_r2',0), stats.get('lin_r',0)))
    return {"answer": answer, "summary": summary}
