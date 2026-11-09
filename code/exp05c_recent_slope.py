"""Experiment 5C: Experiment 5B plus a RECENT warming rate (shared slope fitted on the last K years only).

Why this was tried (declared): after Experiment 5B was frozen, a post-hoc, analysis-only check against
NOAA 2019-2025 observations showed the submitted temperature forecast runs cold (mean error -0.26 F in
2019-2021, -0.65 F in 2022-2025). That prompted the idea; it did NOT pick any setting. The candidates
below were fixed before running, and the choice is made only on held-back origins 1998/2004/2011 with
the unchanged decision rule. No 2019-2025 value is read by this file.

Exp05B uses one shared slope fitted on the full 30-year window. If warming has sped up, a slope fitted
on the window's last K years (K = 15 or 20, fixed) follows the current rate better, at the cost of more
noise. Added candidates (everything else as Exp05B):
  annual_avg_temp   t15s15 / t15s20   15-year level (Exp05B's pick) + shared slope over the last 15 / 20 years
  cdd               cdd10d15 / cdd10d20   Exp05B's daily delta method, with the Tmax and Tmin slopes fitted
                                          over the last 15 / 20 years
New candidates count as more complex than all Exp05B candidates for the 0.01 tie rule.

Run from the repo root:   python code/exp05c_recent_slope.py
Writes outputs/exp05c/: heldout_results.csv, slopes.csv, decision.json (BEFORE the final forecast),
submission_exp05c.csv, run_log.json.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shared import METRICS, REPO, dataset_revision, load_train, valid_flags
import exp02_line_forest as e2
import exp05_levels_slopes as e5
import exp05b_daily_distribution as e5b

ROOT = e2.ROOT
H, MIN_VALID, ORIGINS = e2.H, e2.MIN_VALID, e2.ORIGINS
RECENT_SLOPE = (15, 20)
NEW = {"annual_avg_temp": ["t15s15", "t15s20"], "cdd": ["cdd10d15", "cdd10d20"]}
CANDIDATES = {m: e5b.CANDIDATES[m] + NEW.get(m, []) for m in METRICS}
SIMPLICITY = e5b.SIMPLICITY + ["t15s15", "t15s20", "cdd10d15", "cdd10d20"]
LABEL = {**e5b.LABEL,
         "t15s15": "15-yr level + shared slope over the last 15 years",
         "t15s20": "15-yr level + shared slope over the last 20 years",
         "cdd10d15": "Daily delta method (10 yrs of days), Tmax/Tmin slopes over the last 15 years",
         "cdd10d20": "Daily delta method (10 yrs of days), Tmax/Tmin slopes over the last 20 years"}


def recent_slope(ser, origin, K):
    """Shared slope over each city's valid years in (origin-K, origin]; cities need >= MIN_VALID of them."""
    sub = {c: s[s.index > origin - K] for c, s in ser.items()}
    ok = sorted(c for c, s in sub.items() if len(s) >= MIN_VALID)
    return e5._shared_slope(sub, ok)


def make_new(train_df, cov, days, origin):
    d = train_df[train_df["Year"] <= origin]
    flags = valid_flags(d, cov)
    years = np.arange(origin + 1, origin + H + 1, dtype=float)
    base = e2.make_forecast(train_df, cov, {m: "avg" for m in METRICS}, origin)
    temp = e2._window_series(d, d["Avg Temp"].where(flags["annual_avg_temp"]), origin)
    cdd = e2._window_series(d, d["cdd"].where(flags["cdd"]), origin)
    tx = e2._window_series(d, d["Avg Tmax"].where(d["Miss Tmax"] <= 10), origin)
    tn = e2._window_series(d, d["Avg Tmin"].where(d["Miss Tmin"] <= 10), origin)
    sl = {"origin": origin}
    for K in RECENT_SLOPE:
        sl[f"temp_{K}"] = recent_slope(temp, origin, K)
        sl[f"tmax_{K}"] = recent_slope(tx, origin, K)
        sl[f"tmin_{K}"] = recent_slope(tn, origin, K)
    out = {m: {} for ms in NEW.values() for m in ms}
    for c in sorted(train_df["ID"].unique()):
        k = (c, "annual_avg_temp")
        s = temp.get(c)
        for K in RECENT_SLOPE:
            if s is None or len(s) < MIN_VALID:
                out[f"t15s{K}"][k] = list(base[k])
            else:
                lv = s.iloc[-15:]
                out[f"t15s{K}"][k] = [float(x) for x in lv.mean() + sl[f"temp_{K}"] * (years - lv.index.values.mean())]
        k = (c, "cdd")
        s = cdd.get(c)
        for K in RECENT_SLOPE:
            name = f"cdd10d{K}"
            if s is None or len(s) < MIN_VALID:
                out[name][k] = list(base[k])
                continue
            yrs = s.index.values[-10:]
            piv = yrs.mean()
            pred = []
            for y in years:
                dx, dn = sl[f"tmax_{K}"] * (y - piv), sl[f"tmin_{K}"] * (y - piv)
                pred.append(float(np.mean([np.maximum(0, (days[(c, yy)][0] + dx + days[(c, yy)][1] + dn) / 2 - 65).sum()
                                           for yy in yrs])))
            out[name][k] = pred
    return out, sl


def heldout(train_df, cov, daily, days):
    flags_all = valid_flags(train_df, cov)
    rows, slopes = [], []
    for o in ORIGINS:
        res = e5.make_all(train_df, cov, o)
        res.update(e5b.make_new(train_df, cov, daily, days, o)[0])
        new, sl = make_new(train_df, cov, days, o)
        res.update(new)
        slopes.append(sl)
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
    ap.add_argument("--out-dir", default=str(ROOT / "outputs" / "exp05c"))
    a = ap.parse_args(argv)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    train_df, cov = load_train()
    daily = e5b.load_daily()
    days = e5b.daily_by_city_year(daily)
    res, slopes = heldout(train_df, cov, daily, days)
    res.to_csv(out / "heldout_results.csv", index=False)
    slopes.to_csv(out / "slopes.csv", index=False)
    dec = e5.decide(res, CANDIDATES, SIMPLICITY, LABEL)
    (out / "decision.json").write_text(json.dumps(dec, indent=2))          # before the final forecast

    final = e5.make_all(train_df, cov, 2018)
    final.update(e5b.make_new(train_df, cov, daily, days, 2018)[0])
    new, sl18 = make_new(train_df, cov, days, 2018)
    final.update(new)
    plan = {m: x["method"] for m, x in dec.items()}
    sub = e2.to_rows({k: final[plan[k[1]]][k] for k in final["avg"]})
    assert len(sub) == 210 * 7 * 4 and np.isfinite(sub.predicted_value).all()
    sub.to_csv(out / "submission_exp05c.csv", index=False)
    (out / "run_log.json").write_text(json.dumps({
        "experiment": "exp05c", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "config": {"NEW": NEW, "RECENT_SLOPE": RECENT_SLOPE, "SIMPLICITY": SIMPLICITY, "ORIGINS": ORIGINS,
                   "resolved_plan": plan, "slopes_2018": sl18},
        "dataset": REPO, "dataset_revision": dataset_revision(),
        "packages": {p: version(p) for p in ["pandas", "numpy", "huggingface_hub"]},
        "git_commit": e2.git("rev-parse", "HEAD"), "git_dirty": bool(e2.git("status", "--porcelain"))}, indent=2))
    p = res[res.origin != "average"].pivot_table(index=["metric", "method"], columns="origin", values="skill")
    p["average"] = p.mean(axis=1)
    show = {"annual_avg_temp": ["shared", "r15s", "t15s15", "t15s20"], "cdd": ["r10s", "cdd10d", "cdd10d15", "cdd10d20"]}
    print(p.loc[[(m, x) for m, xs in show.items() for x in xs]].round(3).to_string())
    print(slopes.round(4).to_string(index=False))
    for m, x in dec.items():
        print(f"{m}: {x['method']}  ({x['reason']})")


if __name__ == "__main__":
    main()
