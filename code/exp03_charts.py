"""Charts for experiment 3 (history + forecasts only; run after exp03_shared_slope.py).
    python code/exp03_charts.py"""
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
from exp02_charts import UNIT, pick_cities     # same deterministic cities as exp02
from exp03_shared_slope import EXP03_LABEL, LABEL, METHODS, make_forecast

ROOT = Path(__file__).resolve().parent.parent
STYLE = {"avg": dict(color="tab:green", ls="--"), "line": dict(color="tab:blue", ls="-."),
         "shared": dict(color="tab:purple", ls=":", marker="^", ms=3), "half": dict(color="tab:orange", ls=":", marker="s", ms=3),
         "chosen": dict(color="tab:red", ls="-", lw=1.2)}


def make_charts(out, train_df, cov):
    out = Path(out)
    ch = out / "charts"
    ch.mkdir(parents=True, exist_ok=True)
    dec = json.loads((out / "decision.json").read_text())
    plan = {m: d["method"] for m, d in dec.items()}
    flags = valid_flags(train_df, cov)
    cities = pick_cities(train_df, flags)
    names = train_df.groupby("ID")["Name"].first()
    fcs = {k: make_forecast(train_df, cov, {m: k for m in METRICS}) for k in METHODS}
    fcs["chosen"] = make_forecast(train_df, cov, plan)
    years = np.arange(2019, 2026)
    for m, col in METRICS.items():
        fig, axes = plt.subplots(2, 2, figsize=(11, 7))
        for ax, c in zip(axes.ravel(), cities):
            h = train_df[(train_df.ID == c) & flags[m]]
            h = h[h.Year >= 1960]
            ax.plot(h.Year, h[col], color="black", lw=1, label="valid history")
            for k in METHODS:
                ax.plot(years, fcs[k][(c, m)], label=LABEL[k], **STYLE[k])
            ax.plot(years, fcs["chosen"][(c, m)], label=f"Chosen ({EXP03_LABEL}): {LABEL[plan[m]]}", **STYLE["chosen"])
            ax.set_title(f"{names[c]} ({c}) - {m} ({UNIT[m]})", fontsize=9)
            ax.legend(fontsize=6)
        fig.tight_layout()
        fig.savefig(ch / f"pred_{m}.png", dpi=110)
        plt.close(fig)

    res = pd.read_csv(out / "heldout_results.csv", dtype={"origin": str})
    avg = res[res.origin == "average"].pivot(index="metric", columns="method", values="skill").loc[list(METRICS)]
    fig, ax = plt.subplots(figsize=(10, 4.5))
    w = 0.2
    for i, m in enumerate(METHODS):
        ax.bar(np.arange(len(avg)) + (i - 1.5) * w, avg[m], w, label=LABEL[m] + (" (reference = 0)" if m == "avg" else ""))
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(range(len(avg)), list(avg.index), fontsize=8)
    ax.set_ylabel("held-back skill vs plain average")
    ax.set_title("Exp03: average held-back skill (origins 1998, 2004, 2011)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(ch / "heldout_skill_by_idea.png", dpi=110)
    plt.close(fig)
    print("charts in", ch)


if __name__ == "__main__":
    tr, cv = load_train()
    make_charts(sys.argv[1] if len(sys.argv) > 1 else ROOT / "outputs" / "exp03", tr, cv)
