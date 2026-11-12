
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
