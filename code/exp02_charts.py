"""Charts for experiment 2 (history + forecasts only; run after exp02_line_forest.py).
    python code/exp02_charts.py [--overlay-truth --obs obs_2018_2021.csv]
The overlay adds 2019-2021 observations for analysis only. It is off by default and only
runs after submission_exp02.csv exists."""
import argparse
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
from exp02_line_forest import EXP02_LABEL, LABEL, METHODS, make_forecast

ROOT = Path(__file__).resolve().parent.parent
UNIT = {"annual_avg_temp": "°F", "total_precip_in": "inches", "hottest_day_temp": "°F", "cdd": "°F-days"}
STYLE = {"avg": dict(color="tab:green", ls="--"), "line": dict(color="tab:blue", ls="-."),
         "hybrid": dict(color="tab:orange", ls=":", marker="s", ms=3),
         "chosen": dict(color="tab:red", ls="-", marker="o", ms=3)}
PITTSBURGH = "USW00094823"


def pick_cities(train_df, flags):
    """Pittsburgh, highest and lowest mean Avg Temp, highest mean ToT Prcp (1989-2018).
    Eligible: >=10 valid years in 1989-2018 on all four metrics. Ties by ID; no duplicates."""
    w = train_df["Year"].between(1989, 2018)
    cnt = pd.DataFrame({m: (flags[m] & w).groupby(train_df["ID"]).sum() for m in METRICS})
    elig = sorted(cnt[(cnt >= 10).all(axis=1)].index)
    mean = lambda m: train_df[w & flags[m] & train_df["ID"].isin(elig)].groupby("ID")[METRICS[m]].mean()
    temp, prcp = mean("annual_avg_temp"), mean("total_precip_in")
    order = lambda s, asc: list(s.reset_index().sort_values([s.name, "ID"], ascending=[asc, True])["ID"])
    picks = [PITTSBURGH]
    for ranking in (order(temp, False), order(temp, True), order(prcp, False)):
        picks.append(next(c for c in ranking if c not in picks))
    return picks


def make_charts(out, train_df, cov, overlay_obs=None):
    out = Path(out)
    ch = out / "charts"
    ch.mkdir(parents=True, exist_ok=True)
    dec = json.loads((out / "decision.json").read_text())
    plan = {m: d["method"] for m, d in dec.items()}
    flags = valid_flags(train_df, cov)
    cities = pick_cities(train_df, flags)
    names = train_df.groupby("ID")["Name"].first()
    fcs = {"avg": make_forecast(train_df, cov, {m: "avg" for m in METRICS}),
           "line": make_forecast(train_df, cov, {m: "line" for m in METRICS}),
           "hybrid": make_forecast(train_df, cov, {m: "hybrid" for m in METRICS}),  # always drawn, even if not chosen
           "chosen": make_forecast(train_df, cov, plan)}
    obs = None
    if overlay_obs:  # analysis only; reads the observation file only after the forecast exists
        assert (out / "submission_exp02.csv").exists()
        from truth import annual_from_daily
        t = annual_from_daily(pd.read_csv(overlay_obs, dtype={"DATE": str}))
        obs = t[t.year.between(2019, 2021)]
    cols = {"annual_avg_temp": "avg_temp", "total_precip_in": "tot_prcp", "hottest_day_temp": "max_tmax", "cdd": "cdd"}
    years = np.arange(2019, 2026)
    for m, col in METRICS.items():
        fig, axes = plt.subplots(2, 2, figsize=(11, 7))
        for ax, c in zip(axes.ravel(), cities):
            h = train_df[(train_df.ID == c) & flags[m]]
            h = h[h.Year >= 1960]
            ax.plot(h.Year, h[col], color="black", lw=1, label="valid history")
            for k, lab in (("avg", "Plain average"), ("line", "Plain line"), ("hybrid", "Line + Forest hybrid"), ("chosen", f"Chosen ({EXP02_LABEL}): {LABEL[plan[m]]}")):
                ax.plot(years, fcs[k][(c, m)], label=lab, **STYLE[k])
            if obs is not None:
                o = obs[obs.ID == c]
                ax.plot(o.year, o[cols[m]], "k*", ms=8, label="observed (analysis)")
            ax.set_title(f"{names[c]} ({c}) - {m} ({UNIT[m]})", fontsize=9)
            ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(ch / f"pred_{m}.png", dpi=110)
        plt.close(fig)

    res = pd.read_csv(out / "heldout_results.csv")
    avg = res[res.origin == "average"].pivot(index="metric", columns="method", values="skill").loc[list(METRICS)]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    w = 0.25
    for i, m in enumerate(METHODS):
        ax.bar(np.arange(len(avg)) + (i - 1) * w, avg[m], w, label=LABEL[m] + (" (reference = 0)" if m == "avg" else ""))
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(range(len(avg)), list(avg.index), fontsize=8)
    ax.set_ylabel("held-back skill vs plain average")
    ax.set_title("Average held-back skill (origins 1998, 2004, 2011)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(ch / "heldout_skill_by_method.png", dpi=110)
    plt.close(fig)
    print("charts in", ch)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(ROOT / "outputs" / "exp02"))
    ap.add_argument("--overlay-truth", action="store_true")
    ap.add_argument("--obs", default=None)
    a = ap.parse_args()
    tr, cv = load_train()
    make_charts(a.out_dir, tr, cv, a.obs if a.overlay_truth else None)
