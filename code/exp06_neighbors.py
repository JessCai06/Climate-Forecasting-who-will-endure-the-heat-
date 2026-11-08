"""Experiment 6, step 2: use nearby stations (up to 2018) to make each city's level and slope less noisy.

One station's yearly values carry a lot of local noise. Nearby stations share the same regional weather and
climate trend but have independent noise, so averaging their anomalies gives a cleaner regional signal.

For city c, metric m and origin o (window = the 30 years ending at o):
  - Every station in {c} + neighbors(c) with >= 10 valid years in the window gets an anomaly series:
      temperature, hottest day:  a_t = x_t - mean(x)            (degrees F)
      precipitation, cdd:        a_t = x_t / mean(x) - 1        (fraction; dryer/cooler sites scale differently)
    "Valid" uses the challenge's 10-missing-day rule for that metric (missing days = days in year - days with data).
  - Regional anomaly A_t = equal-weight mean of those anomalies in year t (the city counts as one station).
    For precipitation and cdd, A_t is turned back into the city's units by multiplying by the city's mean.
New candidates (all fixed before running):
  rr15s   city 30-yr mean + mean of A over the last 15 window years, + shared slope from that pivot
  rr10s   same with the last 10 years
  rline   city 30-yr mean + regional slope (OLS of A_t on t) x (year - city pivot)
  rr15l   rr15s's level + regional slope
They compete with exp05's candidates avg, r10, r15, shared, r10s, r15s (so exp05's picks are in the race),
under exp03/exp05's decision rule, unchanged.

Run from the repo root (after code/exp06_fetch_neighbors.py):   python code/exp06_neighbors.py
Writes outputs/exp06/: heldout_results.csv, decision.json (BEFORE the final forecast), submission_exp06.csv,
submission_exp06_<method>_all.csv, run_log.json.

Data rule: reads the challenge data and data/neighbors/annual.csv, both checked to end in 2018.
Never reads observation/truth files.
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
from shared import CUTOFF_YEAR, METRICS, dataset_revision, load_train, valid_flags
import exp02_line_forest as e2
import exp05_levels_slopes as e5

ROOT = e2.ROOT
H, WINDOW, MIN_VALID, ORIGINS, CLIP0 = e2.H, e2.WINDOW, e2.MIN_VALID, e2.ORIGINS, e2.CLIP0
CLOSE = e5.CLOSE
NB_DIR = ROOT / "data" / "neighbors"
OLD = ["avg", "r10", "r15", "shared", "r10s", "r15s"]
NEW = ["rr15s", "rr10s", "rline", "rr15l"]
CANDIDATES = {m: OLD + NEW for m in METRICS}
SIMPLICITY = OLD + NEW
LABEL = {**e5.LABEL, "rr15s": "Regional 15-yr level + shared slope", "rr10s": "Regional 10-yr level + shared slope",
         "rline": "30-yr level + regional slope", "rr15l": "Regional 15-yr level + regional slope"}
RELATIVE = {"total_precip_in", "cdd"}
NB_COL = {"annual_avg_temp": ("avg_temp", ["miss_tmax", "miss_tmin"]), "total_precip_in": ("tot_prcp", ["miss_prcp"]),
          "hottest_day_temp": ("max_tmax", ["miss_tmax"]), "cdd": ("cdd", ["miss_both"])}


def load_neighbors():
    st = pd.read_csv(NB_DIR / "stations.csv")
    ann = pd.read_csv(NB_DIR / "annual.csv")
    if ann.year.max() > CUTOFF_YEAR:
        raise ValueError(f"neighbors: found year > {CUTOFF_YEAR}")
    nb = {}
    for metric, (col, miss) in NB_COL.items():
        ok = (ann[miss].max(axis=1) <= 10) & ann[col].notna()
        v = ann[ok]
        nb[metric] = {sid: g.set_index("year")[col].sort_index() for sid, g in v.groupby("sid")}
    return st.groupby("city_id")["sid"].apply(list).to_dict(), nb


def regional_anomaly(own, others, relative):
    """Equal-weight mean anomaly over the city and its neighbors (each with >= MIN_VALID years)."""
    parts = []
    for s in [own] + others:
        if s is None or len(s) < MIN_VALID:
            continue
        mu = s.mean()
        if relative and mu <= 0:
            continue
        parts.append(s / mu - 1 if relative else s - mu)
    return pd.concat(parts, axis=1).mean(axis=1).sort_index()


def make_all(train_df, cov, nbmap, nb, origin=2018):
    old = e5.make_all(train_df, cov, origin)
    out = {m: old[m] for m in OLD}
    out.update({m: {} for m in NEW})
    d = train_df[train_df["Year"] <= origin]
    flags = valid_flags(d, cov)
    years = np.arange(origin + 1, origin + H + 1, dtype=float)
    lo_w = origin - WINDOW + 1
    for metric, col in METRICS.items():
        ser = e2._window_series(d, d[col].where(flags[metric]), origin)
        enough = sorted(c for c, s in ser.items() if len(s) >= MIN_VALID)
        b = e5._shared_slope(ser, enough)
        lo = 0.0 if metric in CLIP0 else -np.inf
        rel = metric in RELATIVE
        for key, fallback in old["avg"].items():
            c = key[0]
            if key[1] != metric:
                continue
            if c not in enough:
                for m in NEW:
                    out[m][key] = list(fallback)
                continue
            s = ser[c]
            others = [nb[metric][sid].loc[lo_w:origin] for sid in nbmap.get(c, []) if sid in nb[metric]]
            A = regional_anomaly(s, others, rel)
            scale = float(s.mean()) if rel else 1.0
            mean, piv = float(s.mean()), float(s.index.values.mean())
            slope_r = float(np.polyfit(A.index.values.astype(float), A.values, 1)[0]) * scale
            lev = {}
            for k in (10, 15):
                tail = A.iloc[-k:]
                lev[k] = (mean + float(tail.mean()) * scale, float(tail.index.values.mean()))

            def path(lv, p, sl):
                return [float(x) for x in np.maximum(lv + sl * (years - p), lo)]

            out["rr15s"][key] = path(*lev[15], b)
            out["rr10s"][key] = path(*lev[10], b)
            out["rline"][key] = path(mean, piv, slope_r)
            out["rr15l"][key] = path(*lev[15], slope_r)
    return out


def heldout(train_df, cov, nbmap, nb, origins=ORIGINS):
    flags_all = valid_flags(train_df, cov)
    rows = []
    for o in origins:
        res = make_all(train_df, cov, nbmap, nb, o)
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


def decide(res):
    return e5.decide(res, CANDIDATES, SIMPLICITY, LABEL)   # exp05's rule, this experiment's candidate set


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(ROOT / "outputs" / "exp06"))
    a = ap.parse_args(argv)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    train_df, cov = load_train()
    nbmap, nb = load_neighbors()
    res = heldout(train_df, cov, nbmap, nb)
    res.to_csv(out / "heldout_results.csv", index=False)
    dec = decide(res)
    (out / "decision.json").write_text(json.dumps(dec, indent=2))          # before any final forecast

    final = make_all(train_df, cov, nbmap, nb, 2018)
    plan = {m: d["method"] for m, d in dec.items()}
    files = {"submission_exp06.csv": {k: final[plan[k[1]]][k] for k in final["avg"]}}
    for m in NEW:
        files[f"submission_exp06_{m}_all.csv"] = final[m]
    for name, fc in files.items():
        sub = e2.to_rows(fc)
        assert len(sub) == 210 * 7 * 4 and np.isfinite(sub.predicted_value).all()
        assert (sub[sub.metric.isin(CLIP0)].predicted_value >= 0).all()
        sub.to_csv(out / name, index=False)
    (out / "run_log.json").write_text(json.dumps({
        "experiment": "exp06", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "config": {"CANDIDATES": CANDIDATES, "SIMPLICITY": SIMPLICITY, "CLOSE": CLOSE, "WINDOW": WINDOW,
                   "ORIGINS": ORIGINS, "MIN_VALID": MIN_VALID, "RELATIVE": sorted(RELATIVE), "resolved_plan": plan},
        "neighbors": {"stations": int(sum(len(v) for v in nbmap.values())),
                      "unique_stations": int(len({s for v in nbmap.values() for s in v}))},
        "dataset": "CMU-OSPO/protostar-climate-train-to-2018", "dataset_revision": dataset_revision(),
        "packages": {p: version(p) for p in ["pandas", "numpy", "huggingface_hub"]},
        "git_commit": e2.git("rev-parse", "HEAD"), "git_dirty": bool(e2.git("status", "--porcelain"))}, indent=2))
    for m, d in dec.items():
        print(f"{m}: {d['method']}  ({d['reason']})")
    print("wrote", out)


if __name__ == "__main__":
    main()
