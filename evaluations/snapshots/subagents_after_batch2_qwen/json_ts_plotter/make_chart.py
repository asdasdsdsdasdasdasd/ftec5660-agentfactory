
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

d = json.load(open("plot_data.json"))
spec = d["spec"]
years = d["years"]
ys = d["values"]
ct = spec.get("chart_type", "line")

fig, ax = plt.subplots(figsize=(14, 8))
if ct == "bar":
    ax.bar([str(y) for y in years], ys, color="steelblue")
    plt.xticks(rotation=90)
elif ct == "scatter":
    ax.scatter(years, ys, color="steelblue")
else:
    ax.plot(years, ys, marker="o", linewidth=2, markersize=4, color="steelblue")

if ys:
    max_i = max(range(len(ys)), key=lambda i: ys[i])
    ax.annotate("Peak: %s (%.2f)" % (years[max_i], ys[max_i]),
                xy=(years[max_i], ys[max_i]),
                xytext=(10, 10), textcoords="offset points",
                fontsize=11, color="red",
                arrowprops=dict(arrowstyle="->", color="red"))

ax.set_title(spec.get("title", "Time Series"), fontsize=16, fontweight="bold")
ax.set_xlabel(spec.get("x_label", "Year"), fontsize=13)
ax.set_ylabel(spec.get("y_label", "Value"), fontsize=13)
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig("population_chart.png", dpi=130)
print("SAVED population_chart.png with", len(years), "points")
