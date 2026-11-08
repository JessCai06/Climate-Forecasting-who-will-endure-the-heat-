"""Experiment 4: use city locations (neighbor table, gap filling, regional slopes).

Run from the repo root:   python code/exp04_neighbors.py [--charts]
Order of writing (outputs/exp04/): distances.csv (cache), step0_counts.csv, masking_test.csv,
gapfill_limit.json (BEFORE any forecast), heldout_results.csv, decision.json (BEFORE the final
forecast), submission_exp04.csv (+ *_reg500_all / _reg1000_all / _filled_all), filled_values.csv, run_log.json.
Score it (analysis only):  python code/starter_score.py obs_2018_2021.csv

Data rule: only data up to 2018 is read (neighbors too); this module never reads observation/truth files.
Filled values are flagged, are never scored and never enter a slope estimate; they only help the
city's own level (mean and mean year) in the "filled" candidate.
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
from exp04_step0 import step0

ROOT = e2.ROOT
H, WINDOW, MIN_VALID, SEED, ORIGINS, CLIP0 = e2.H, e2.WINDOW, e2.MIN_VALID, e2.SEED, e2.ORIGINS, e2.CLIP0
CLOSE = 0.01                                   # same rule as exp03
RADII = {"reg500": 500.0, "reg1000": 1000.0}   # regional slope radii (km); global shared = infinite radius
LIMITS = [150, 300, 500]                       # gap-fill distance limits (km), chosen by the masking test
FILL_METRICS = ["annual_avg_temp", "cdd"]      # gap filling only for these
MIN_NBRS, MIN_OVERLAP, MIN_CORR = 3, 15, 0.6   # gap-fill requirements
MASK_FRAC = 0.15
METHODS = ["avg", "line", "shared", "reg500", "reg1000", "filled"]
SIMPLICITY = ["avg", "line", "shared", "reg1000", "reg500", "filled"]
SLOPE_CANDS = ["shared", "reg500", "reg1000"]
LABEL = {"avg": "A Plain average", "line": "B Own line", "shared": "C Global shared slope",
         "reg500": "E Regional slope 500 km", "reg1000": "F Regional slope 1000 km", "filled": "G Best slope + filled gaps"}
EXP04_LABEL = "Exp04 chosen per metric"
SCORER_LABELS = {"reg500": "Regional slope 500 km (all metrics)", "reg1000": "Regional slope 1000 km (all metrics)",
                 "filled": "Best slope + filled gaps (all metrics)"}


# ------------------------------------------------------------- STEP 1: neighbor table
def city_table(train_df):
    t = train_df.groupby("ID")[["Lat", "Lon"]].first().sort_index()
    return t


def haversine_matrix(lat, lon):
    la, lo = np.radians(lat), np.radians(lon)
    dlat, dlon = la[:, None] - la[None, :], lo[:, None] - lo[None, :]
    a = np.sin(dlat / 2) ** 2 + np.cos(la)[:, None] * np.cos(la)[None, :] * np.sin(dlon / 2) ** 2
    return 2 * 6371.0088 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def distance_table(train_df, path):
    """210x210 haversine distances (km), cached as CSV (rebuilt only if missing or the city list changed)."""
    t = city_table(train_df)
    path = Path(path)
    if path.exists():
        cached = pd.read_csv(path, index_col=0)
        if list(cached.index) == list(t.index) and list(cached.columns) == list(t.index):
            return cached
    dist = pd.DataFrame(haversine_matrix(t.Lat.values, t.Lon.values), index=t.index, columns=t.index)
    dist.round(3).to_csv(path)
    return pd.read_csv(path, index_col=0)


# ------------------------------------------------------------------- windows
def window_matrix(d, flags, metric, origin, cities):
    """cities x 30 years matrix of valid values (NaN = invalid/missing), years ending at `origin`."""
    yrs = np.arange(origin - WINDOW + 1, origin + 1)
    v = d[METRICS[metric]].where(flags[metric])
    m = d["Year"].between(yrs[0], origin) & v.notna()
    piv = d.loc[m].assign(v=v[m]).pivot(index="ID", columns="Year", values="v")
    return piv.reindex(index=cities, columns=yrs), yrs


# ------------------------------------------------------------------ STEP 2: gap filling
def fill_gaps(M, dist, limit):
    """M: cities x years (NaN = gap). Returns (filled M copy, boolean fill mask).
    Fill = own mean + weighted mean of neighbor deviations (weight = corr * (1 - d / (2*limit)),
    closer and better correlated neighbors count more). A neighbor qualifies if within `limit` km,
    >= 15 overlapping valid years with the city and correlation of deviations >= 0.6; >= 3 qualifying
    neighbors must have the year. Otherwise the gap stays."""
    X = M.values
    n = X.shape[0]
    mean = np.array([np.nanmean(r) if (~np.isnan(r)).any() else np.nan for r in X])
    D = X - mean[:, None]
    D0 = np.where(np.isnan(D), 0.0, D)
    V = (~np.isnan(D)).astype(float)
    cnt = V @ V.T                                         # overlapping years
    sxy = D0 @ D0.T
    sxx = (D0 ** 2) @ V.T                                  # sum of c's squared dev over overlap with n
    syy = V @ (D0 ** 2).T                                  # sum of n's squared dev over overlap with c
    # Pearson on deviations from each city's full-window mean (the spec's "correlation of past deviations")
    with np.errstate(invalid="ignore", divide="ignore"):
        corr = sxy / np.sqrt(sxx * syy)
    dm = dist.values
    qual = (dm <= limit) & (cnt >= MIN_OVERLAP) & (corr >= MIN_CORR) & ~np.eye(n, dtype=bool)
    W = np.where(qual, corr * (1 - dm / (2 * limit)), 0.0)
    num = W @ D0                                           # sum w * dev over neighbors with that year valid
    den = W @ V
    nb = qual.astype(float) @ V                            # qualifying neighbors having the year
    gap = np.isnan(X)
    fillm = gap & (nb >= MIN_NBRS) & (den > 0) & ~np.isnan(mean)[:, None]
    out = X.copy()
    out[fillm] = (mean[:, None] + np.divide(num, den, out=np.zeros_like(num), where=den > 0))[fillm]
    return pd.DataFrame(out, index=M.index, columns=M.columns), pd.DataFrame(fillm, index=M.index, columns=M.columns)


def masking_test(train_df, cov, dist, seed=SEED):
    """Hide 15% of known valid window values (origin 2018) at random, fill them with each limit and
    compare MAE with linear interpolation of the same city series. Pooled MAE is reported on the points
    every limit could fill (comparable), plus each limit's own set."""
    cities = sorted(train_df.ID.unique())
    d = train_df[train_df.Year <= 2018]
    flags = valid_flags(d, cov)
    rows = []
    for metric in FILL_METRICS:
        M, yrs = window_matrix(d, flags, metric, 2018, cities)
        X = M.values
        rng = np.random.default_rng(seed)
        known = np.argwhere(~np.isnan(X))
        hide = known[rng.random(len(known)) < MASK_FRAC]
        Xm = X.copy()
        Xm[hide[:, 0], hide[:, 1]] = np.nan
        Mm = pd.DataFrame(Xm, index=M.index, columns=M.columns)
        # linear interpolation of the same series (edges held at the nearest value)
        interp = np.full(len(hide), np.nan)
        for k, (i, j) in enumerate(hide):
            ok = ~np.isnan(Xm[i])
            if ok.any():
                interp[k] = np.interp(yrs[j], yrs[ok], Xm[i][ok])
        truth = X[hide[:, 0], hide[:, 1]]
        per = {}
        for L in LIMITS:
            fm, fl = fill_gaps(Mm, dist, L)
            per[L] = fl.values[hide[:, 0], hide[:, 1]], fm.values[hide[:, 0], hide[:, 1]]
        common = np.logical_and.reduce([per[L][0] for L in LIMITS]) & ~np.isnan(interp)
        for L in LIMITS:
            fl, fv = per[L]
            own = fl & ~np.isnan(interp)
            rows.append({"metric": metric, "limit_km": L, "n_hidden": len(hide),
                         "n_filled": int(fl.sum()), "n_common": int(common.sum()),
                         "fill_mae_common": float(np.abs(fv[common] - truth[common]).mean()),
                         "interp_mae_common": float(np.abs(interp[common] - truth[common]).mean()),
                         "fill_mae_own_set": float(np.abs(fv[own] - truth[own]).mean()),
                         "interp_mae_own_set": float(np.abs(interp[own] - truth[own]).mean())})
    return pd.DataFrame(rows)


def choose_limits(mt):
    """Lowest fill MAE on the common set, per metric (ties: smaller limit)."""
    out = {}
    for m, g in mt.groupby("metric"):
        g = g.sort_values(["fill_mae_common", "limit_km"])
        out[m] = int(g.iloc[0].limit_km)
    return out


# --------------------------------------------------------------- forecasts
def make_forecast(train_df, cov, dist, metric_plan, origin=2018, limits=None, filled_slope=None,
                  return_filled=False):
    """{(city_id, metric): [v(origin+1) .. v(origin+7)]}. metric_plan maps metric -> one of METHODS.
    'filled' needs limits[metric] (km) and filled_slope[metric] (one of SLOPE_CANDS): the slope comes from
    real values only; the city's level (mean and mean year) uses real + filled values."""
    assert_cutoff(train_df, "train_df")
    cities = sorted(train_df["ID"].unique())
    d = train_df[train_df["Year"] <= origin]
    flags = valid_flags(d, cov)
    years = np.arange(origin + 1, origin + H + 1, dtype=float)
    base = e2.make_forecast(train_df, cov, {m: ("avg" if p == "avg" else "line") for m, p in metric_plan.items()}, origin)
    out, fills = {}, []
    dm = dist.reindex(index=cities, columns=cities).values
    for metric, method in metric_plan.items():
        if method not in METHODS:
            raise ValueError(f"{metric}: method '{method}' unknown")
        if method in ("avg", "line"):
            out.update({k: v for k, v in base.items() if k[1] == metric})
            continue
        slope_m = method
        if method == "filled":
            if metric not in FILL_METRICS:
                raise ValueError(f"{metric}: gap filling is only for {FILL_METRICS}")
            slope_m = filled_slope[metric]
        M, yrs = window_matrix(d, flags, metric, origin, cities)
        X = M.values
        valid = ~np.isnan(X)
        enough = valid.sum(1) >= MIN_VALID
        # per-city real-data statistics (slope never sees filled values)
        cnt = valid.sum(1)
        xmean = np.array([yrs[v].mean() if v.any() else np.nan for v in valid])
        ymean = np.array([X[i][valid[i]].mean() if valid[i].any() else np.nan for i in range(len(cities))])
        dx = np.where(valid, yrs[None, :] - xmean[:, None], 0.0)
        dy = np.where(valid, X - ymean[:, None], 0.0)
        sxy, sxx = (dx * dy).sum(1), (dx * dx).sum(1)
        use = enough.astype(float)
        if slope_m == "shared":
            near = np.ones_like(dm, dtype=bool)
        else:
            near = dm <= RADII[slope_m]
        member = near * use[None, :]                       # row c: cities pooled for c (self included if enough)
        num, den = member @ sxy, member @ sxx
        slope = np.divide(num, den, out=np.zeros_like(num), where=den > 0)
        level_y, level_x = ymean.copy(), xmean.copy()
        if method == "filled":
            Fm, fl = fill_gaps(M, dist.reindex(index=cities, columns=cities), limits[metric])
            Xf, vf = Fm.values, ~np.isnan(Fm.values)
            level_y = np.array([Xf[i][vf[i]].mean() if vf[i].any() else np.nan for i in range(len(cities))])
            level_x = np.array([yrs[v].mean() if v.any() else np.nan for v in vf])
            for i, j in np.argwhere(fl.values):
                if enough[i]:
                    fills.append({"origin": origin, "city_id": cities[i], "metric": metric,
                                  "year": int(yrs[j]), "filled_value": float(Xf[i, j]), "is_filled": True})
        lo = 0.0 if metric in CLIP0 else -np.inf
        for i, c in enumerate(cities):
            if enough[i]:
                vals = level_y[i] + slope[i] * (years - level_x[i])
                out[(c, metric)] = [float(x) for x in np.maximum(vals, lo)]
            else:
                out[(c, metric)] = base[(c, metric)]
    return (out, pd.DataFrame(fills)) if return_filled else out


# ---------------------------------------------------------------- held-back test
def heldout(train_df, cov, dist, limits, origins=ORIGINS):
    """All candidates; 'filled' (temp, cdd only) uses, per metric, the slope candidate with the highest
    average held-back skill among shared/reg500/reg1000 (ties: simpler). Truth = real valid values only."""
    flags_all = valid_flags(train_df, cov)
    plain = {}
    rows = []
    # first pass: non-filled candidates, per origin
    fc = {o: {m: make_forecast(train_df, cov, dist, {k: m for k in METRICS}, o) for m in METHODS if m != "filled"}
          for o in origins}

    def score(o, metric, res_by_method):
        col = METRICS[metric]
        past = train_df["Year"] <= o
        v = train_df[col].where(flags_all[metric])
        win = e2._window_series(train_df[past], v[past], o)
        ok = {c for c, s in win.items() if len(s) >= MIN_VALID}
        t = train_df.assign(v=v)[train_df["Year"].between(o + 1, o + H)].dropna(subset=["v"])   # real values only
        t = t[t["ID"].isin(ok)]
        return {m: float(np.mean([abs(res_by_method[m][(r.ID, metric)][r.Year - o - 1] - r.v) for r in t.itertuples()]))
                for m in res_by_method}, len(t)

    mae, n = {}, {}
    for o in origins:
        for metric in METRICS:
            mae[(o, metric)], n[(o, metric)] = score(o, metric, fc[o])
    avg_skill = lambda metric, m: np.mean([1 - mae[(o, metric)][m] / mae[(o, metric)]["avg"] for o in origins])
    best_slope = {metric: sorted(SLOPE_CANDS, key=lambda m: (-avg_skill(metric, m), SIMPLICITY.index(m)))[0]
                  for metric in METRICS}
    for metric in FILL_METRICS:
        for o in origins:
            f = make_forecast(train_df, cov, dist, {metric: "filled"}, o, limits, best_slope)
            m_f, _ = score(o, metric, {**{"avg": fc[o]["avg"]}, "filled": {**fc[o]["avg"], **f}})
            mae[(o, metric)]["filled"] = m_f["filled"]
    for (o, metric), mm in mae.items():
        for m, x in mm.items():
            rows.append({"metric": metric, "method": m, "origin": str(o), "mae": x,
                         "skill": 1 - x / mm["avg"], "n": n[(o, metric)]})
    df = pd.DataFrame(rows)
    avg = df.groupby(["metric", "method"], sort=False)[["mae", "skill", "n"]].mean().reset_index()
    avg.insert(2, "origin", "average")
    return pd.concat([df, avg], ignore_index=True), best_slope


def decide(res, best_slope):
    """Exp03's rule over the candidates that exist for each metric: 1) highest average skill; 2) must beat
    the plain average in >=2 of 3 origins, else A; 3) lead over the runner-up < 0.01 -> the simpler of the two
    (order: average, own line, global shared, regional 1000, regional 500, filled); the simpler pick must
    also pass step 2, otherwise A."""
    dec = {}
    for metric in METRICS:
        r = res[res.metric == metric]
        methods = [m for m in METHODS if m in set(r.method)]
        sk = {m: float(r[(r.method == m) & (r.origin == "average")].skill.iloc[0]) for m in methods}
        per = {m: {o: float(x) for o, x in zip(r[(r.method == m) & (r.origin != "average")].origin,
                                               r[(r.method == m) & (r.origin != "average")].skill)} for m in methods}
        beats = {m: sum(per[m][o] > 0 for o in per[m]) for m in methods}
        ranked = sorted(methods, key=lambda m: (-sk[m], SIMPLICITY.index(m)))
        winner, second = ranked[0], ranked[1]
        lead = sk[winner] - sk[second]
        info = {"avg_skill": sk, "per_origin_skill": per, "origins_beating_plain_average": beats,
                "ranked_by_avg_skill": ranked, "highest": winner, "runner_up": second, "lead_over_runner_up": lead,
                "slope_candidate_used_by_filled": best_slope[metric]}
        pick, why = winner, f"{LABEL[winner]} has the highest average skill"
        if pick != "avg" and beats[pick] < 2:
            pick, why = "avg", f"rule 2: {LABEL[winner]} beat the plain average in only {beats[winner]} of 3 origins"
        elif lead < CLOSE:
            simpler = min((winner, second), key=SIMPLICITY.index)
            if simpler != winner:
                pick, why = simpler, f"rule 3: lead of {lead:.4f} over {LABEL[second]} is under {CLOSE}, so the simpler idea wins"
            else:
                why += f" (lead {lead:.4f} < {CLOSE}, but it is also the simpler one)"
            if pick != "avg" and beats[pick] < 2:
                pick, why = "avg", why + f"; but {LABEL[pick]} beat the plain average in only {beats[pick]} of 3 origins (rule 2)"
        info.update(method=pick, reason=why)
        dec[metric] = info
    return dec


# ------------------------------------------------------------------------ main
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(ROOT / "outputs" / "exp04"))
    ap.add_argument("--charts", action="store_true")
    a = ap.parse_args(argv)
    out = Path(a.out_dir)
    (out / "charts").mkdir(parents=True, exist_ok=True)

    train_df, cov = load_train()
    # STEP 0 (report only)
    s0 = step0(train_df, cov)
    s0.to_csv(out / "step0_counts.csv", index=False)
    print("STEP 0 counts (city-metrics):\n", s0.to_string(index=False))
    # STEP 1
    dist = distance_table(train_df, out / "distances.csv")
    # STEP 2: pick the distance limit by the masking test, write it before any forecast
    mt = masking_test(train_df, cov, dist)
    mt.to_csv(out / "masking_test.csv", index=False)
    limits = choose_limits(mt)
    (out / "gapfill_limit.json").write_text(json.dumps(
        {"limit_km_per_metric": limits, "rule": "lowest fill MAE on the points every limit could fill",
         "grid_km": LIMITS, "mask_fraction": MASK_FRAC, "seed": SEED}, indent=2))
    print("\nMasking test:\n", mt.round(3).to_string(index=False), "\nchosen limits:", limits)
    # held-back test and decision (before any final forecast)
    res, best_slope = heldout(train_df, cov, dist, limits)
    res.to_csv(out / "heldout_results.csv", index=False)
    dec = decide(res, best_slope)
    (out / "decision.json").write_text(json.dumps(dec, indent=2))
    plan = {m: d["method"] for m, d in dec.items()}
    # final forecasts
    fill_rows = []
    variants = [("submission_exp04.csv", plan)] + [(f"submission_exp04_{k}_all.csv", {m: k for m in METRICS})
                                                  for k in ("reg500", "reg1000")]
    # "filled" applied to all metrics: filled where available, the best slope candidate (real values) elsewhere
    variants.append(("submission_exp04_filled_all.csv", {m: ("filled" if m in FILL_METRICS else best_slope[m]) for m in METRICS}))
    for name, p in variants:
        fc, fills = make_forecast(train_df, cov, dist, p, 2018, limits, best_slope, return_filled=True)
        sub = e2.to_rows(fc)
        assert len(sub) == 210 * 7 * 4 and np.isfinite(sub.predicted_value).all()
        assert (sub[sub.metric.isin(CLIP0)].predicted_value >= 0).all()
        sub.to_csv(out / name, index=False)
        if name == "submission_exp04_filled_all.csv" and len(fills):
            fills.to_csv(out / "filled_values.csv", index=False)
    (out / "run_log.json").write_text(json.dumps({
        "experiment": "exp04", "scorer_labels": [EXP04_LABEL] + list(SCORER_LABELS.values()),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "config": {"METHODS": METHODS, "SIMPLICITY": SIMPLICITY, "RADII": RADII, "LIMITS": LIMITS, "CLOSE": CLOSE,
                   "MIN_NBRS": MIN_NBRS, "MIN_OVERLAP": MIN_OVERLAP, "MIN_CORR": MIN_CORR, "MASK_FRAC": MASK_FRAC,
                   "WINDOW": WINDOW, "ORIGINS": ORIGINS, "SEED": SEED, "gapfill_limits": limits,
                   "slope_candidate_for_filled": best_slope, "resolved_plan": plan},
        "dataset": "CMU-OSPO/protostar-climate-train-to-2018", "dataset_revision": dataset_revision(),
        "packages": {p: version(p) for p in ["pandas", "numpy", "scikit-learn", "matplotlib", "huggingface_hub"]},
        "git_commit": e2.git("rev-parse", "HEAD"), "git_dirty": bool(e2.git("status", "--porcelain"))}, indent=2))
    for m, d in dec.items():
        print(f"{m}: {d['method']}  ({d['reason']})")
    print("wrote", out)
    if a.charts:
        from exp04_charts import make_charts
        make_charts(out, train_df, cov, dist, limits, best_slope)


if __name__ == "__main__":
    main()
