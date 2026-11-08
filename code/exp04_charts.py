"""Charts for experiment 4 (history + forecasts only; run after exp04_neighbors.py).
    python code/exp04_charts.py"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shared import METRICS, load_train, valid_flags
from exp02_charts import UNIT, pick_cities
import exp04_neighbors as e4

ROOT = Path(__file__).resolve().parent.parent
STYLE = {"avg": dict(color="tab:green", ls="--"), "line": dict(color="tab:blue", ls="-."),
         "shared": dict(color="tab:purple", ls=":", marker="^", ms=3), "reg500": dict(color="tab:brown", ls=":", marker="s", ms=3),
         "reg1000": dict(color="tab:cyan", ls=":", marker="d", ms=3), "filled": dict(color="tab:orange", ls=":", marker="x", ms=4),
         "chosen": dict(color="tab:red", ls="-", lw=1.2)}


def make_charts(out, train_df, cov, dist, limits, best_slope):
    out = Path(out)
    ch = out / "charts"
    ch.mkdir(parents=True, exist_ok=True)
    dec = json.loads((out / "decision.json").read_text())
    plan = {m: d["method"] for m, d in dec.items()}
    flags = valid_flags(train_df, cov)
    cities = pick_cities(train_df, flags)
    names = train_df.groupby("ID")["Name"].first()
    fcs = {k: e4.make_forecast(train_df, cov, dist, {m: k for m in METRICS if k != "filled" or m in e4.FILL_METRICS},
                               2018, limits, best_slope) for k in e4.METHODS}
    fcs["chosen"] = e4.make_forecast(train_df, cov, dist, plan, 2018, limits, best_slope)
    years = np.arange(2019, 2026)
    for m, col in METRICS.items():
        fig, axes = plt.subplots(2, 2, figsize=(11, 7))
        for ax, c in zip(axes.ravel(), cities):
            h = train_df[(train_df.ID == c) & flags[m]]
            h = h[h.Year >= 1960]
            ax.plot(h.Year, h[col], color="black", lw=1, label="valid history")
            for k in e4.METHODS:
                if (c, m) in fcs[k]:
                    ax.plot(years, fcs[k][(c, m)], label=e4.LABEL[k], **STYLE[k])
            ax.plot(years, fcs["chosen"][(c, m)], label=f"Chosen ({e4.EXP04_LABEL}): {e4.LABEL[plan[m]]}", **STYLE["chosen"])
            ax.set_title(f"{names[c]} ({c}) - {m} ({UNIT[m]})", fontsize=9)
            ax.legend(fontsize=5)
        fig.tight_layout()
        fig.savefig(ch / f"pred_{m}.png", dpi=110)
        plt.close(fig)
    res = pd.read_csv(out / "heldout_results.csv", dtype={"origin": str})
    avg = res[res.origin == "average"].pivot(index="metric", columns="method", values="skill").loc[list(METRICS)]
    fig, ax = plt.subplots(figsize=(11, 4.5))
    w = 0.14
    for i, m in enumerate(e4.METHODS):
        ax.bar(np.arange(len(avg)) + (i - 2.5) * w, avg[m].fillna(0), w, label=e4.LABEL[m] + (" (reference = 0)" if m == "avg" else ""))
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(range(len(avg)), list(avg.index), fontsize=8)
    ax.set_ylabel("held-back skill vs plain average")
    ax.set_title("Exp04: average held-back skill (origins 1998, 2004, 2011); filled only for temp and cdd")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(ch / "heldout_skill_by_idea.png", dpi=110)
    plt.close(fig)
    print("charts in", ch)


if __name__ == "__main__":
    tr, cv = load_train()
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "outputs" / "exp04"
    dist = e4.distance_table(tr, out / "distances.csv")
    lim = json.loads((out / "gapfill_limit.json").read_text())["limit_km_per_metric"]
    dec = json.loads((out / "decision.json").read_text())
    make_charts(out, tr, cv, dist, lim, {m: d["slope_candidate_used_by_filled"] for m, d in dec.items()})
