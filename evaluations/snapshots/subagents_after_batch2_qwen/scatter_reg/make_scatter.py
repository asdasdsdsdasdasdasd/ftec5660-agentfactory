import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

with open("scatter_data.json") as f:
    d = json.load(f)
spec = d["spec"]
pts = d["points"]
xs = np.array([p["x"] for p in pts], dtype=float)
ys = np.array([p["y"] for p in pts], dtype=float)
labels = [p.get("label", "") for p in pts]

fig, ax = plt.subplots(figsize=(11, 7))
ax.scatter(xs, ys, s=70, color="#1f77b4", edgecolors="black", zorder=3, label="Data points")
for x, y, lb in zip(xs, ys, labels):
    if lb:
        ax.annotate(str(lb), (x, y), textcoords="offset points", xytext=(5, 5), fontsize=7, color="#333")

stats = {}
stats["n"] = int(len(xs))
if spec.get("fit_line", True) and len(xs) >= 2:
    slope, intercept = np.polyfit(xs, ys, 1)
    xs_line = np.linspace(xs.min(), xs.max(), 100)
    ys_line = slope * xs_line + intercept
    y_pred = slope * xs + intercept
    ss_res = float(np.sum((ys - y_pred) ** 2))
    ss_tot = float(np.sum((ys - ys.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    r = float(np.corrcoef(xs, ys)[0, 1])
    ax.plot(xs_line, ys_line, color="#d62728", linewidth=2.5, zorder=2, label="Regression line")
    eq = "y = {:.6g}*x + {:.6g}".format(slope, intercept)
    box = eq + chr(10) + "R^2 = {:.4f}".format(r2) + chr(10) + "r = {:.4f}".format(r) + chr(10) + "n = {}".format(len(xs))
    ax.text(0.03, 0.97, box, transform=ax.transAxes, fontsize=10, va="top", ha="left",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.85, edgecolor="gray"))
    stats["slope"] = float(slope)
    stats["intercept"] = float(intercept)
    stats["r2"] = r2
    stats["r"] = r

ax.set_title(spec.get("title", "Scatter"), fontsize=14, fontweight="bold")
ax.set_xlabel(spec.get("x_label", "X"), fontsize=11)
ax.set_ylabel(spec.get("y_label", "Y"), fontsize=11)
ax.grid(True, alpha=0.3)
ax.legend(loc="lower right")
fig.tight_layout()
fig.savefig("scatter_regression.png", dpi=140)
with open("fit_stats.json", "w") as f:
    json.dump(stats, f, indent=2)
print("SAVED scatter_regression.png with", len(xs), "points")
print(json.dumps(stats))
