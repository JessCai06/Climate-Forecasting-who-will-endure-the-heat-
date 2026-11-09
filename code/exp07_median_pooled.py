"""Experiment 7: match the forecast to the scoring rule (medians) and blend each city's slope with the shared one.

1. Medians. The score is mean absolute error, and the value that minimises absolute error is the median of the
   distribution, not its mean. Precipitation and cdd are skewed, so their means sit above the typical year.
     med       the city's 30-year median (flat)
     *_m       a trend candidate shifted by the median of the city's residuals around its 30-year shared-slope
               line (that line's residuals have mean 0, so the shift is median - mean of the residuals)
2. Partially pooled slopes (empirical Bayes). A city's own 30-year slope is real information but noisy; the
   shared slope is steady but the same everywhere. Each city gets
       slope_c = w_c * own_c + (1 - w_c) * shared,   w_c = tau2 / (tau2 + se_c^2)
   where se_c^2 is the sampling variance of the city's own slope (residual variance / sum of squared year
   deviations) and tau2 the spread of true slopes across cities, estimated by moments:
   max(0, variance of own slopes - mean se^2). Nothing is tuned: w_c comes from the data's own noise.
     pool      30-year level + pooled slope        r10p / r15p   recent 10 / 15-year level + pooled slope

Candidates (fixed before running), for every metric:
  avg, shared, r10s, r15s  (exp05's, so exp05's picks are in the race)
  med, r10s_m, r15s_m, pool, r10p, r15p, r10p_m, r15p_m
Decision rule: exp03/exp05's, unchanged (highest average held-back skill over origins 1998/2004/2011; must beat
the plain average in >= 2 of 3 origins; a lead under 0.01 over the runner-up goes to the simpler of the two).

Run from the repo root:   python code/exp07_median_pooled.py
Writes outputs/exp07/: heldout_results.csv, decision.json (BEFORE the final forecast), submission_exp07.csv,
submission_exp07_<method>_all.csv, pooling.json, run_log.json.

Data rule: only the challenge data up to 2018 is read (shared.load_train guards it); never reads
observation/truth files.
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
from shared import METRICS, assert_cutoff, dataset_revision, load_train, valid_flags
import exp02_line_forest as e2
import exp05_levels_slopes as e5

ROOT = e2.ROOT
H, WINDOW, MIN_VALID, ORIGINS, CLIP0 = e2.H, e2.WINDOW, e2.MIN_VALID, e2.ORIGINS, e2.CLIP0
CLOSE = e5.CLOSE
OLD = ["avg", "shared", "r10s", "r15s"]
NEW = ["med", "r10s_m", "r15s_m", "pool", "r10p", "r15p", "r10p_m", "r15p_m"]
SIMPLICITY = ["avg", "med", "shared", "r10s", "r15s", "r10s_m", "r15s_m", "pool", "r10p", "r15p", "r10p_m", "r15p_m"]
CANDIDATES = {m: SIMPLICITY for m in METRICS}
LABEL = {**e5.LABEL, "med": "30-yr median", "r10s_m": "Recent 10-yr level + shared slope, median-shifted",
         "r15s_m": "Recent 15-yr level + shared slope, median-shifted", "pool": "30-yr level + pooled slope",
         "r10p": "Recent 10-yr level + pooled slope", "r15p": "Recent 15-yr level + pooled slope",
         "r10p_m": "Recent 10-yr level + pooled slope, median-shifted",
         "r15p_m": "Recent 15-yr level + pooled slope, median-shifted"}


def pooled_slopes(ser, cities, shared):
    """Empirical-Bayes blend of each city's own OLS slope with the shared slope."""
    own, se2 = {}, {}
    for c in cities:
        x, y = ser[c].index.values.astype(float), ser[c].values
        xd = x - x.mean()
        sxx = float((xd ** 2).sum())
        b = float((xd * (y - y.mean())).sum() / sxx)
        resid = y - y.mean() - b * xd
        own[c] = b
        se2[c] = float((resid ** 2).sum() / (len(y) - 2) / sxx)
    tau2 = max(0.0, float(np.var(list(own.values()), ddof=1)) - float(np.mean(list(se2.values()))))
    w = {c: tau2 / (tau2 + se2[c]) if tau2 + se2[c] > 0 else 0.0 for c in cities}
    return {c: w[c] * own[c] + (1 - w[c]) * shared for c in cities}, {"tau2": tau2, "mean_w": float(np.mean(list(w.values())))}


def make_all(train_df, cov, origin=2018, info=None):
    assert_cutoff(train_df, "train_df")
    old = e5.make_all(train_df, cov, origin)
    out = {m: old[m] for m in OLD}
    out.update({m: {} for m in NEW})
    d = train_df[train_df["Year"] <= origin]
    flags = valid_flags(d, cov)
    years = np.arange(origin + 1, origin + H + 1, dtype=float)
    for metric, col in METRICS.items():
        ser = e2._window_series(d, d[col].where(flags[metric]), origin)
        enough = sorted(c for c, s in ser.items() if len(s) >= MIN_VALID)
        b = e5._shared_slope(ser, enough)
        bp, stats = pooled_slopes(ser, enough, b)
        if info is not None:
            info[metric] = {"shared_slope": b, **stats}
        lo = 0.0 if metric in CLIP0 else -np.inf
        for key, fallback in old["avg"].items():
            if key[1] != metric:
                continue
            c = key[0]
            if c not in enough:
                for m in NEW:
                    out[m][key] = list(fallback)
                continue
            s = ser[c]
            yrs = s.index.values.astype(float)
            mean, piv = float(s.mean()), float(yrs.mean())
            shift = float(np.median(s.values - (mean + b * (yrs - piv))))   # median of shared-line residuals
            rec = {k: (float(s.iloc[-k:].mean()), float(s.index.values[-k:].mean())) for k in (10, 15)}

            def path(lv, p, sl, sh=0.0):
                return [float(x) for x in np.maximum(lv + sh + sl * (years - p), lo)]

            out["med"][key] = [float(max(np.median(s.values), lo))] * H
            out["r10s_m"][key] = path(*rec[10], b, shift)
            out["r15s_m"][key] = path(*rec[15], b, shift)
            out["pool"][key] = path(mean, piv, bp[c])
            out["r10p"][key] = path(*rec[10], bp[c])
            out["r15p"][key] = path(*rec[15], bp[c])
            out["r10p_m"][key] = path(*rec[10], bp[c], shift)
            out["r15p_m"][key] = path(*rec[15], bp[c], shift)
    return out


def heldout(train_df, cov, origins=ORIGINS):
    flags_all = valid_flags(train_df, cov)
    rows = []
    for o in origins:
        res = make_all(train_df, cov, o)
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
    return pd.concat([df, avg], ignore_index=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(ROOT / "outputs" / "exp07"))
    a = ap.parse_args(argv)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    train_df, cov = load_train()
    res = heldout(train_df, cov)
    res.to_csv(out / "heldout_results.csv", index=False)
    dec = e5.decide(res, CANDIDATES, SIMPLICITY, LABEL)
    (out / "decision.json").write_text(json.dumps(dec, indent=2))          # before any final forecast

    info = {}
    final = make_all(train_df, cov, 2018, info)
    (out / "pooling.json").write_text(json.dumps(info, indent=2))
    plan = {m: d["method"] for m, d in dec.items()}
    files = {"submission_exp07.csv": {k: final[plan[k[1]]][k] for k in final["avg"]}}
    for m in NEW:
        files[f"submission_exp07_{m}_all.csv"] = final[m]
    for name, fc in files.items():
        sub = e2.to_rows(fc)
        assert len(sub) == 210 * 7 * 4 and np.isfinite(sub.predicted_value).all()
        assert (sub[sub.metric.isin(CLIP0)].predicted_value >= 0).all()
        sub.to_csv(out / name, index=False)
    (out / "run_log.json").write_text(json.dumps({
        "experiment": "exp07", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "config": {"CANDIDATES": SIMPLICITY, "SIMPLICITY": SIMPLICITY, "CLOSE": CLOSE, "WINDOW": WINDOW,
                   "ORIGINS": ORIGINS, "MIN_VALID": MIN_VALID, "resolved_plan": plan},
        "dataset": "CMU-OSPO/protostar-climate-train-to-2018", "dataset_revision": dataset_revision(),
        "packages": {p: version(p) for p in ["pandas", "numpy", "huggingface_hub"]},
        "git_commit": e2.git("rev-parse", "HEAD"), "git_dirty": bool(e2.git("status", "--porcelain"))}, indent=2))
    for m, d in dec.items():
        print(f"{m}: {d['method']}  ({d['reason']})")
    print("wrote", out)


if __name__ == "__main__":
    main()
