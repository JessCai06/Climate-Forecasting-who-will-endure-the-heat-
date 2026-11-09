"""Experiment 5B: Experiment 5 plus two candidates built from each city's DAILY highs and lows.

Exp05 is unchanged (same candidates, held-back origins 1998/2004/2011, decision rule). Exp05B only ADDS:

  1. Hottest day from the distribution of daily highs.
     The single hottest day is noisy, so its own trend is poorly estimated. The 95th percentile of a
     year's daily highs (about the 18th-hottest day) moves with the same heat but is far steadier.
     Forecast = level of the annual hottest day + shared slope of the annual 95th percentile of daily
     highs x (year - level's middle year).
        h30p95   level = 30-year mean of the hottest day
        h15p95   level = mean of the last 15 valid years (the OCN window Exp05 uses for temperature)

  2. cdd from the distribution of daily highs and lows ("delta method").
     cdd = sum over days of max(0, (Tmax + Tmin)/2 - 65), which is non-linear: a 1 F warming adds many
     degree days in Miami and few in Seattle. Exp05 adds one cdd slope for every city. Instead, take the
     city's actual days from its last K valid cdd years, warm every day's high by the shared slope of
     annual mean Tmax and every day's low by the shared slope of annual mean Tmin (nights can warm at a
     different rate), times (year - those years' middle year), and recompute cdd. With no warming this
     is exactly Exp05's recent-K level, so the only change is how warming turns into cdd.
        cdd10d   K = 10 (Exp05's cdd pick uses the last 10 years)
        cdd15d   K = 15

Candidates are fixed before running. New candidates count as more complex than all Exp05 candidates
for the 0.01 tie rule. Slopes, levels and days are computed only from data up to each origin.

Run from the repo root:   python code/exp05b_daily_distribution.py
Writes outputs/exp05b/: heldout_results.csv, slopes.csv, decision.json (BEFORE the final forecast),
submission_exp05b.csv, run_log.json.

Note: uses the fixed shared.valid_flags (2026-11-08), so Exp05's cdd held-back numbers here are the
corrected ones (r10s 0.112, not the 0.086 in Exp05's own outputs). Exp05's forecast is unchanged by the fix.
Data rule: only data up to 2018 is read; no 2019-2025 value is used.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
from huggingface_hub import hf_hub_download

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shared import CUTOFF_YEAR, METRICS, REPO, dataset_revision, load_train, valid_flags
import exp02_line_forest as e2
import exp05_levels_slopes as e5

ROOT = e2.ROOT
H, WINDOW, MIN_VALID, ORIGINS = e2.H, e2.WINDOW, e2.MIN_VALID, e2.ORIGINS
NEW = {"hottest_day_temp": ["h30p95", "h15p95"], "cdd": ["cdd10d", "cdd15d"]}
CANDIDATES = {m: e5.CANDIDATES[m] + NEW.get(m, []) for m in METRICS}
SIMPLICITY = e5.SIMPLICITY + ["h30p95", "h15p95", "cdd10d", "cdd15d"]
LABEL = {**e5.LABEL, "h30p95": "30-yr level + shared slope of daily-high 95th percentile",
         "h15p95": "15-yr level + shared slope of daily-high 95th percentile",
         "cdd10d": "Last 10 yrs of days, highs/lows warmed by shared slopes (delta method)",
         "cdd15d": "Last 15 yrs of days, highs/lows warmed by shared slopes (delta method)"}


def load_daily():
    d = pd.read_parquet(hf_hub_download(REPO, "daily/train-00000-of-00001.parquet", repo_type="dataset"))
    d["Date"] = pd.to_datetime(d["Date"].astype(str))
    assert d["Date"].max() <= pd.Timestamp(f"{CUTOFF_YEAR}-12-31"), "daily data after 2018"
    d["Year"] = d["Date"].dt.year
    return d[d["Year"] >= 1960][["ID", "Year", "tmax", "tmin"]].reset_index(drop=True)


def daily_by_city_year(daily):
    """{(city, year): (tmax array, tmin array)} for days with both readings (the days cdd counts)."""
    b = daily.dropna(subset=["tmax", "tmin"])
    return {k: (g.tmax.to_numpy(float), g.tmin.to_numpy(float)) for k, g in b.groupby(["ID", "Year"])}


def make_new(train_df, cov, daily, days, origin):
    """New candidates: {method: {(city, metric): [7 floats]}}; cities without enough data get Exp05's avg."""
    d = train_df[train_df["Year"] <= origin]
    flags = valid_flags(d, cov)
    years = np.arange(origin + 1, origin + H + 1, dtype=float)
    base = e2.make_forecast(train_df, cov, {m: "avg" for m in METRICS}, origin)
    cities = sorted(train_df["ID"].unique())

    def series(v):
        return e2._window_series(d, v, origin)

    hot = series(d["Max Tmax"].where(flags["hottest_day_temp"]))
    cdd = series(d["cdd"].where(flags["cdd"]))
    tx = series(d["Avg Tmax"].where(d["Miss Tmax"] <= 10))
    tn = series(d["Avg Tmin"].where(d["Miss Tmin"] <= 10))
    p95 = (daily[daily.Year.between(origin - WINDOW + 1, origin)].groupby(["ID", "Year"]).tmax.quantile(0.95)
           .rename("p95").reset_index())
    p95 = p95.merge(d[["ID", "Year", "Miss Tmax"]], on=["ID", "Year"])
    p95 = {c: g.set_index("Year").p95 for c, g in p95[p95["Miss Tmax"] <= 10].groupby("ID")}

    def enough(ser):
        return sorted(c for c, s in ser.items() if len(s) >= MIN_VALID)

    slope = {"p95": e5._shared_slope(p95, enough(p95)), "tmax": e5._shared_slope(tx, enough(tx)),
             "tmin": e5._shared_slope(tn, enough(tn)), "hot_own": e5._shared_slope(hot, enough(hot))}

    out = {m: {} for ms in NEW.values() for m in ms}
    for c in cities:
        k = (c, "hottest_day_temp")
        s = hot.get(c)
        if s is None or len(s) < MIN_VALID:
            out["h30p95"][k] = out["h15p95"][k] = list(base[k])
        else:
            for name, sub in (("h30p95", s), ("h15p95", s.iloc[-15:])):
                out[name][k] = [float(x) for x in sub.mean() + slope["p95"] * (years - sub.index.values.mean())]
        k = (c, "cdd")
        s = cdd.get(c)
        for K in (10, 15):
            name = f"cdd{K}d"
            if s is None or len(s) < MIN_VALID:
                out[name][k] = list(base[k])
                continue
            yrs = s.index.values[-K:]
            piv = yrs.mean()
            pred = []
            for y in years:
                dx, dn = slope["tmax"] * (y - piv), slope["tmin"] * (y - piv)
                vals = [np.maximum(0, (days[(c, yy)][0] + dx + days[(c, yy)][1] + dn) / 2 - 65).sum() for yy in yrs]
                pred.append(float(np.mean(vals)))
            out[name][k] = pred
    return out, slope


def heldout(train_df, cov, daily, days):
    """Exp05's scoring (pooled MAE over valid city-years of cities with >= 10 valid window years)."""
    flags_all = valid_flags(train_df, cov)
    rows, slopes = [], []
    for o in ORIGINS:
        res = e5.make_all(train_df, cov, o)
        new, sl = make_new(train_df, cov, daily, days, o)
        res.update(new)
        slopes.append({"origin": o, **sl})
        past = train_df["Year"] <= o
        for metric, col in METRICS.items():
            v = train_df[col].where(flags_all[metric])
            win = e2._window_series(train_df[past], v[past], o)
            ok = {c for c, s in win.items() if len(s) >= MIN_VALID}
            t = train_df.assign(v=v)[train_df["Year"].between(o + 1, o + H)].dropna(subset=["v"])
            t = t[t["ID"].isin(ok)]
            mae = {m: float(np.mean([abs(res[m][(r.ID, metric)][r.Year - o - 1] - r.v) for r in t.itertuples()]))
                   for m in CANDIDATES[metric]}
            for m in CANDIDATES[metric]:
                rows.append({"metric": metric, "method": m, "origin": str(o), "mae": mae[m],
                             "skill": 1 - mae[m] / mae["avg"], "n": len(t)})
    df = pd.DataFrame(rows)
    avg = df.groupby(["metric", "method"], sort=False)[["mae", "skill", "n"]].mean().reset_index()
    avg.insert(2, "origin", "average")
    return pd.concat([df, avg], ignore_index=True), pd.DataFrame(slopes)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(ROOT / "outputs" / "exp05b"))
    a = ap.parse_args(argv)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    train_df, cov = load_train()
    daily = load_daily()
    days = daily_by_city_year(daily)
    res, slopes = heldout(train_df, cov, daily, days)
    res.to_csv(out / "heldout_results.csv", index=False)
    slopes.to_csv(out / "slopes.csv", index=False)
    dec = e5.decide(res, CANDIDATES, SIMPLICITY, LABEL)
    (out / "decision.json").write_text(json.dumps(dec, indent=2))          # before the final forecast

    final = e5.make_all(train_df, cov, 2018)
    new, sl18 = make_new(train_df, cov, daily, days, 2018)
    final.update(new)
    plan = {m: x["method"] for m, x in dec.items()}
    chosen = {k: final[plan[k[1]]][k] for k in final["avg"]}
    sub = e2.to_rows(chosen)
    assert len(sub) == 210 * 7 * 4 and np.isfinite(sub.predicted_value).all()
    sub.to_csv(out / "submission_exp05b.csv", index=False)
    for m in [x for ms in NEW.values() for x in ms]:
        e2.to_rows({k: (final[m] if m in CANDIDATES[k[1]] else final[plan[k[1]]])[k] for k in final["avg"]}).to_csv(
            out / f"submission_exp05b_{m}.csv", index=False)
    (out / "run_log.json").write_text(json.dumps({
        "experiment": "exp05b", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "config": {"NEW": NEW, "SIMPLICITY": SIMPLICITY, "ORIGINS": ORIGINS, "resolved_plan": plan,
                   "slopes_2018": sl18},
        "dataset": REPO, "dataset_revision": dataset_revision(),
        "packages": {p: version(p) for p in ["pandas", "numpy", "huggingface_hub"]},
        "git_commit": e2.git("rev-parse", "HEAD"), "git_dirty": bool(e2.git("status", "--porcelain"))}, indent=2))
    p = res[res.origin != "average"].pivot_table(index=["metric", "method"], columns="origin", values="skill")
    p["average"] = p.mean(axis=1)
    print(p[p.index.get_level_values(0).isin(["hottest_day_temp", "cdd"])].round(3).to_string())
    print(slopes.round(4).to_string(index=False))
    for m, x in dec.items():
        print(f"{m}: {x['method']}  ({x['reason']})")
    print("wrote", out)


if __name__ == "__main__":
    main()
