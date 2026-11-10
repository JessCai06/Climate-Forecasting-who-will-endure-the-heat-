"""Experiment 9: fill the city station's MISSING DAYS from nearby stations, then rerun Experiment 5 unchanged.

Only gaps are filled. A real reading at the city's station is never changed.

How a missing day at city c is filled (per variable: tmax, tmin, prcp):
  - Neighbors: Iris' Experiment 6 list (data/neighbors/stations.csv: up to 8 GHCN-Daily stations within
    100 km), daily data 1969-2018 from NOAA's Access Data Service with endDate=2018-12-31.
  - Calibration, AS OF THE ORIGIN: for held-back origin O, each neighbor's correction is fitted only on
    days in the 30-year window (O-29 .. O) when both the city and the neighbor reported. Temperature:
    city minus neighbor, mean per calendar month. Precipitation: city total / neighbor total per calendar
    month (clipped to 0.25..4). A neighbor needs >= 365 shared days in the window to be used.
  - Estimate = weighted mean over the neighbors that reported that day of (neighbor value corrected),
    weight = 1 / (variance of that neighbor's daily calibration error). Temperatures are rounded to whole
    degrees F and rain to 0.01 in, like the station data.
  - A year is filled for a variable only if the station missed at most MAX_FILL days of it (fixed in
    advance: 90). Years with longer gaps are left as they are.
After filling, the yearly values are rebuilt with the challenge's own definitions (checked to reproduce
annual_indices exactly: see check_rebuild) and the 10-missing-days rule is applied to what is still missing.

Data variants (the forecast method is Experiment 5's pick per metric, unchanged):
  orig     the challenge data (reproduces Experiment 5 exactly)
  rescue   only years that are INVALID in the original data (11..MAX_FILL missing days) are filled;
           valid years keep their original values
  fillall  every year with 1..MAX_FILL missing days is filled
Scoring: held-back origins 1998/2004/2011, truth = ORIGINAL valid city-years only (filled values are never
scored), same cities as Experiment 5. Skill = 1 - MAE / MAE of Experiment 5's plain average on the
original data. Decision rule = Experiment 3/5's (fixed before running): highest average skill; must beat
`orig` in >= 2 of 3 origins; a lead under 0.01 goes to the simpler variant (orig, rescue, fillall).

Also a masking test: in complete years 1989-2018, hide one random 30-day block per city-year, fill it, and
compare the rebuilt yearly value with the real one (vs leaving the gap).

Run from the repo root (needs the cached neighbor files, see code/exp06_fetch_neighbors.py):
    python code/exp09_daily_gapfill.py
Writes outputs/exp09/: rebuild_check.csv, mask_test.csv, fill_counts.csv, heldout_results.csv,
decision.json (BEFORE the final forecast), submission_exp09.csv, run_log.json.

Data rule: every input is dated on or before 2018-12-31 (asserted). No 2019-2025 value is read.
"""
import argparse
import calendar
import json
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shared import CUTOFF_YEAR, METRICS, REPO, dataset_revision, load_train, valid_flags, train_file
import exp02_line_forest as e2
import exp05_levels_slopes as e5

ROOT = e2.ROOT
RAW = ROOT / "data" / "raw" / "daily"
NEIGHBORS = ROOT / "data" / "neighbors" / "stations.csv"
FIRST_YEAR, MAX_FILL, MIN_OVERLAP, SEED = 1969, 90, 365, 42
ORIGINS, H, WINDOW, MIN_VALID, CLOSE = e2.ORIGINS, e2.H, e2.WINDOW, e2.MIN_VALID, 0.01
VARIANTS = ["orig", "rescue", "fillall"]                       # simplest first
EXP05_PICK = {"annual_avg_temp": "r15s", "cdd": "r10s", "total_precip_in": "avg", "hottest_day_temp": "avg"}
VARS = ("tmax", "tmin", "prcp")


# ------------------------------------------------------------------ data
def load_city_daily():
    d = pd.read_parquet(train_file("daily/train-00000-of-00001.parquet"))
    d["Date"] = pd.to_datetime(d["Date"].astype(str))
    assert d["Date"].max() <= pd.Timestamp(f"{CUTOFF_YEAR}-12-31"), "city daily data after 2018"
    return d[d["Date"].dt.year >= FIRST_YEAR].reset_index(drop=True)


def load_neighbor(sid):
    """Neighbor daily values in F and inches, with Iris' quality checks (exp06_fetch_neighbors)."""
    p = RAW / f"{sid}.csv"
    if not p.exists():
        return None
    n = pd.read_csv(p, dtype={"STATION": str, "DATE": str})
    if n.empty:
        return None
    n["Date"] = pd.to_datetime(n["DATE"])
    assert n["Date"].max() <= pd.Timestamp(f"{CUTOFF_YEAR}-12-31"), f"{sid}: data after 2018"
    for c in ("TMAX", "TMIN", "PRCP"):
        n[c] = pd.to_numeric(n[c], errors="coerce") if c in n else np.nan
    n.loc[~n.TMAX.between(-62, 57), "TMAX"] = np.nan
    n.loc[~n.TMIN.between(-62, 57), "TMIN"] = np.nan
    n.loc[n.TMIN > n.TMAX, ["TMAX", "TMIN"]] = np.nan
    n.loc[~n.PRCP.between(0, 1000), "PRCP"] = np.nan
    return pd.DataFrame({"tmax": n.TMAX * 9 / 5 + 32, "tmin": n.TMIN * 9 / 5 + 32,
                         "prcp": n.PRCP / 25.4}).set_index(n["Date"])


def annual_from_daily(d):
    """Yearly values with the challenge's definitions (verified by check_rebuild)."""
    tavg = (d.tmax + d.tmin) / 2
    g = d.assign(Year=d["Date"].dt.year, tavg=tavg, cddd=np.maximum(0, tavg - 65)).groupby(["ID", "Year"])
    out = pd.DataFrame({"Avg Temp": (g.tmax.mean() + g.tmin.mean()) / 2, "ToT Prcp": g.prcp.sum(min_count=1),
                        "Max Tmax": g.tmax.max(), "cdd": g.cddd.sum(min_count=1),
                        "n_tmax": g.tmax.count(), "n_tmin": g.tmin.count(), "n_prcp": g.prcp.count(),
                        "Days Both": g.tavg.count()}).reset_index()
    days = out.Year.map(lambda y: 366 if calendar.isleap(y) else 365)
    for v in VARS:
        out[f"Miss {v.capitalize()}"] = days - out.pop(f"n_{v}")
    return out


def check_rebuild(city, train_df, cov):
    r = annual_from_daily(city).merge(train_df, on=["ID", "Year"], suffixes=("", "_ch")).merge(
        cov[["ID", "Year", "Days Both"]], on=["ID", "Year"], suffixes=("", "_ch"))
    rows = []
    for col, tol in [("Avg Temp", .01), ("ToT Prcp", .01), ("Max Tmax", .01), ("cdd", .5), ("Miss Tmax", 0),
                     ("Miss Tmin", 0), ("Miss Prcp", 0), ("Days Both", 0)]:
        x, y = r[col], r[f"{col}_ch"]
        both = x.notna() & y.notna()
        diff = (x - y).abs()[both]
        rows.append({"column": col, "rows": int(both.sum()), "share_match": float((diff <= tol + 1e-9).mean()),
                     "worst_diff": float(diff.max())})
    df = pd.DataFrame(rows)
    assert (df.share_match >= 0.99).all(), f"rebuild does not match annual_indices:\n{df}"
    return df


# ------------------------------------------------------------------ filling
def city_arrays(city, nb):
    """{city_id: (dates, T[days, 3], N[days, k, 3])} aligned on the city's dates."""
    out = {}
    for cid, g in city.groupby("ID"):
        g = g.set_index("Date")
        frames = [f for f in (load_neighbor(s) for s in nb.get(cid, [])) if f is not None]
        T = g[list(VARS)].to_numpy(float)
        N = (np.stack([f.reindex(g.index)[list(VARS)].to_numpy(float) for f in frames], axis=1)
             if frames else np.full((len(g), 0, 3), np.nan))
        out[cid] = (g.index, T, N)
    return out


def fill_city(dates, T, N, origin, eligible):
    """Estimates for every day (NaN where no neighbor can help), calibrated on window days <= origin."""
    years, month = dates.year.to_numpy(), dates.month.to_numpy() - 1
    cal = (years >= origin - WINDOW + 1) & (years <= origin)
    est = np.full(T.shape, np.nan)
    for j, v in enumerate(VARS):
        num, den = np.zeros(len(T)), np.zeros(len(T))
        for k in range(N.shape[1]):
            t, n = T[:, j], N[:, k, j]
            both = cal & ~np.isnan(t) & ~np.isnan(n)
            if both.sum() < MIN_OVERLAP:
                continue
            corr = np.full(12, np.nan)
            for mo in range(12):
                b = both & (month == mo)
                if b.sum() < 20:
                    continue
                if v == "prcp":
                    corr[mo] = np.clip(t[b].sum() / n[b].sum(), 0.25, 4) if n[b].sum() > 0 else 1.0
                else:
                    corr[mo] = (t[b] - n[b]).mean()
            pred = n * corr[month] if v == "prcp" else n + corr[month]
            err = (t - pred)[both]
            err = err[~np.isnan(err)]
            if len(err) < MIN_OVERLAP:
                continue
            w = 1.0 / max(err.var(), 1e-6)
            ok = ~np.isnan(pred)
            num[ok] += w * pred[ok]
            den[ok] += w
        with np.errstate(invalid="ignore", divide="ignore"):
            e = num / den
        est[:, j] = np.round(e, 2 if v == "prcp" else 0)
    est[~eligible] = np.nan
    return est


def filled_daily(arrs, origin, mask_days=None):
    """City daily table with gaps filled (only years with <= MAX_FILL missing days of that variable)."""
    parts = []
    for cid, (dates, T, N) in arrs.items():
        T = T.copy()
        if mask_days is not None and cid in mask_days:
            T[mask_days[cid]] = np.nan
        yrs = pd.Series(dates.year)
        miss = pd.DataFrame(np.isnan(T), columns=VARS).groupby(yrs.values).transform("sum").to_numpy()
        eligible = miss <= MAX_FILL
        est = fill_city(dates, T, N, origin, eligible)
        F = np.where(np.isnan(T), est, T)
        parts.append(pd.DataFrame({"ID": cid, "Date": dates, "tmax": F[:, 0], "tmin": F[:, 1], "prcp": F[:, 2]}))
    return pd.concat(parts, ignore_index=True)


# ------------------------------------------------------------------ variants
def preflagged(train_df, cov, values):
    """train_df/cov where each metric column holds only its valid values and nothing counts as missing,
    so shared.valid_flags returns exactly `values.notna()`: lets Exp05 run unchanged on any data variant."""
    t = train_df.copy()
    for col in METRICS.values():
        t[col] = values[col].to_numpy()
    t[["Miss Tmax", "Miss Tmin", "Miss Prcp"]] = 0
    c = cov.copy()
    c["Days Both"] = c.Year.map(lambda y: 366 if calendar.isleap(y) else 365)
    return t, c


def variant_values(train_df, cov, fa):
    """{variant: DataFrame of valid metric values aligned to train_df}. fa = annual from the filled daily."""
    flags = valid_flags(train_df, cov)
    orig = pd.DataFrame({col: train_df[col].where(flags[m]) for m, col in METRICS.items()})
    cols = ["Avg Temp", "ToT Prcp", "Max Tmax", "cdd", "Miss Tmax", "Miss Tmin", "Miss Prcp", "Days Both"]
    base = train_df[["ID", "Year"] + cols[:7]].merge(cov[["ID", "Year", "Days Both"]], on=["ID", "Year"], how="left")
    new = base[["ID", "Year"]].merge(fa[["ID", "Year"] + cols], on=["ID", "Year"], how="left")
    has = new["Year"].ge(FIRST_YEAR) & new["Miss Tmax"].notna()   # years before 1969 keep the original values
    for col in cols:
        base.loc[has, col] = new.loc[has, col].to_numpy()
    fa = base
    fflags = valid_flags(fa.drop(columns="Days Both"), fa[["ID", "Year", "Days Both"]])
    fill = pd.DataFrame({col: fa[col].where(fflags[m]) for m, col in METRICS.items()})
    rescue = orig.copy()
    for m, col in METRICS.items():
        rescue[col] = orig[col].where(flags[m], fill[col])
    return {"orig": orig, "rescue": rescue, "fillall": fill}


# ------------------------------------------------------------------ masking test
def mask_test(arrs, rng):
    """Hide a random 30-day block in each complete city-year 1989-2018; fill (origin 2018) and rebuild."""
    mask, truth_rows = {}, []
    for cid, (dates, T, _) in arrs.items():
        idx = np.zeros(len(T), bool)
        for y in range(1989, 2019):
            ii = np.where(dates.year == y)[0]
            if len(ii) and not np.isnan(T[ii]).any():
                s = rng.integers(0, len(ii) - 30)
                idx[ii[s:s + 30]] = True
                truth_rows.append((cid, y))
        mask[cid] = idx
    real = pd.concat([pd.DataFrame({"ID": c, "Date": d, "tmax": T[:, 0], "tmin": T[:, 1], "prcp": T[:, 2]})
                      for c, (d, T, _) in arrs.items()], ignore_index=True)
    gap = real.copy()
    m_all = np.concatenate([mask[c] for c in arrs])
    gap.loc[m_all, list(VARS)] = np.nan
    filled = filled_daily(arrs, 2018, mask)
    keys = pd.DataFrame(truth_rows, columns=["ID", "Year"])
    a_real, a_gap, a_fill = (keys.merge(annual_from_daily(x), on=["ID", "Year"]) for x in (real, gap, filled))
    daily_err = {v: float(np.nanmean(np.abs(filled[v].to_numpy()[m_all] - real[v].to_numpy()[m_all]))) for v in VARS}
    rows = []
    for col in METRICS.values():
        rows.append({"value": col, "city_years": len(keys),
                     "mae_leave_gap": float((a_gap[col] - a_real[col]).abs().mean()),
                     "mae_filled": float((a_fill[col] - a_real[col]).abs().mean()),
                     "share_still_missing_days": float(np.isnan(filled[["tmax", "tmin", "prcp"]].to_numpy()[m_all]).mean())})
    df = pd.DataFrame(rows)
    df.attrs["daily_mae"] = daily_err
    return df


# ------------------------------------------------------------------ held-back test
def heldout(train_df, cov, arrs):
    flags_all = valid_flags(train_df, cov)
    rows, counts = [], []
    for o in ORIGINS:
        vals = variant_values(train_df, cov, annual_from_daily(filled_daily(arrs, o)))
        preds = {}
        for var, v in vals.items():
            t, c = preflagged(train_df, cov, v)
            preds[var] = e5.make_all(t, c, o)
        past = train_df["Year"] <= o
        for metric, col in METRICS.items():
            truth = train_df[col].where(flags_all[metric])
            win = e2._window_series(train_df[past], truth[past], o)
            ok = {c for c, s in win.items() if len(s) >= MIN_VALID}
            tt = train_df.assign(v=truth)[train_df["Year"].between(o + 1, o + H)].dropna(subset=["v"])
            tt = tt[tt["ID"].isin(ok)]
            inwin = train_df["Year"].between(o - WINDOW + 1, o)
            gained = {c for c, g in train_df[inwin].assign(a=vals["orig"][col][inwin].notna(),
                                                           b=vals["rescue"][col][inwin].notna()).groupby("ID")
                      if (g.b & ~g.a).any()}
            counts.append({"origin": o, "metric": metric,
                           "window_years_orig": int(vals["orig"][col][inwin].notna().sum()),
                           "window_years_filled": int(vals["rescue"][col][inwin].notna().sum()),
                           "cities_gaining_years": len(gained)})
            base = np.mean([abs(preds["orig"]["avg"][(r.ID, metric)][r.Year - o - 1] - r.v) for r in tt.itertuples()])
            for var in VARIANTS:
                for sub, sel in (("all", tt), ("gap_cities", tt[tt.ID.isin(gained)])):
                    if sub == "gap_cities" and sel.empty:
                        continue
                    e = [abs(preds[var][EXP05_PICK[metric]][(r.ID, metric)][r.Year - o - 1] - r.v) for r in sel.itertuples()]
                    b = [abs(preds["orig"]["avg"][(r.ID, metric)][r.Year - o - 1] - r.v) for r in sel.itertuples()]
                    rows.append({"metric": metric, "variant": var, "subset": sub, "origin": str(o),
                                 "mae": float(np.mean(e)), "skill": 1 - np.mean(e) / np.mean(b), "n": len(sel)})
    df = pd.DataFrame(rows)
    avg = df.groupby(["metric", "variant", "subset"], sort=False)[["mae", "skill", "n"]].mean().reset_index()
    avg.insert(3, "origin", "average")
    return pd.concat([df, avg], ignore_index=True), pd.DataFrame(counts)


def decide(res):
    dec = {}
    r0 = res[res.subset == "all"]
    for metric in METRICS:
        r = r0[r0.metric == metric]
        sk = {v: float(r[(r.variant == v) & (r.origin == "average")].skill.iloc[0]) for v in VARIANTS}
        per = {v: r[(r.variant == v) & (r.origin != "average")].set_index("origin").skill.astype(float).to_dict()
               for v in VARIANTS}
        beats = {v: sum(per[v][o] > per["orig"][o] for o in per[v]) for v in VARIANTS}
        ranked = sorted(VARIANTS, key=lambda v: (-sk[v], VARIANTS.index(v)))
        win, second = ranked[0], ranked[1]
        pick, why = win, f"{win} has the highest average skill"
        if sk[win] - sk[second] < CLOSE and VARIANTS.index(second) < VARIANTS.index(win):
            pick, why = second, f"lead of {sk[win] - sk[second]:.4f} over {second} is under {CLOSE}: simpler wins"
        if pick != "orig" and (sk[pick] - sk["orig"] < CLOSE or beats[pick] < 2):
            why += f"; {pick} does not beat orig by {CLOSE} in average skill and in >= 2 of 3 origins, so orig"
            pick = "orig"
        dec[metric] = {"method": EXP05_PICK[metric], "avg_skill": sk, "per_origin_skill": per,
                       "origins_beating_orig": beats, "variant": pick, "reason": why}
    return dec


# ------------------------------------------------------------------ main
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(ROOT / "outputs" / "exp09"))
    a = ap.parse_args(argv)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)

    train_df, cov = load_train()
    city = load_city_daily()
    check_rebuild(city, train_df, cov).to_csv(out / "rebuild_check.csv", index=False)
    nb = pd.read_csv(NEIGHBORS).groupby("city_id").sid.apply(list).to_dict()
    arrs = city_arrays(city, nb)
    n_nb = {c: N.shape[1] for c, (_, _, N) in arrs.items()}
    print(f"neighbors loaded: {sum(n_nb.values())} pairs, {sum(v == 0 for v in n_nb.values())} cities with none")

    # sanity: the orig variant reproduces Experiment 5's forecast exactly
    v18 = variant_values(train_df, cov, annual_from_daily(filled_daily(arrs, 2018)))
    t, c = preflagged(train_df, cov, v18["orig"])
    e5_ref, e5_mine = e5.make_all(train_df, cov, 2018), e5.make_all(t, c, 2018)
    assert all(np.allclose(e5_ref[m][k], e5_mine[m][k]) for m in e5_ref for k in e5_ref[m]), "orig != Exp05"

    mt = mask_test(arrs, rng)
    mt.to_csv(out / "mask_test.csv", index=False)
    print("masking test (30-day gap in a complete year):\n", mt.to_string(index=False), "\n daily MAE:", mt.attrs["daily_mae"])

    res, counts = heldout(train_df, cov, arrs)
    res.to_csv(out / "heldout_results.csv", index=False)
    counts.to_csv(out / "fill_counts.csv", index=False)
    dec = decide(res)
    (out / "decision.json").write_text(json.dumps(dec, indent=2))          # before the final forecast

    final = {}
    for var in VARIANTS:
        t, c = preflagged(train_df, cov, v18[var])
        final[var] = e5.make_all(t, c, 2018)
    chosen = {k: final[dec[m]["variant"]][EXP05_PICK[m]][k] for m in METRICS for k in final["orig"]["avg"] if k[1] == m}
    sub = e2.to_rows(chosen)
    assert len(sub) == 210 * 7 * 4 and np.isfinite(sub.predicted_value).all()
    sub.to_csv(out / "submission_exp09.csv", index=False)
    for var in ("rescue", "fillall"):
        e2.to_rows({k: final[var][EXP05_PICK[k[1]]][k] for k in final["orig"]["avg"]}).to_csv(
            out / f"submission_exp09_{var}_all.csv", index=False)
    (out / "run_log.json").write_text(json.dumps({
        "experiment": "exp09", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "config": {"MAX_FILL": MAX_FILL, "MIN_OVERLAP": MIN_OVERLAP, "FIRST_YEAR": FIRST_YEAR, "VARIANTS": VARIANTS,
                   "EXP05_PICK": EXP05_PICK, "ORIGINS": ORIGINS, "CLOSE": CLOSE, "SEED": SEED,
                   "resolved_plan": {m: d["variant"] for m, d in dec.items()}},
        "masking_daily_mae": mt.attrs["daily_mae"], "neighbor_pairs_loaded": sum(n_nb.values()),
        "dataset": REPO, "dataset_revision": dataset_revision(),
        "packages": {p: version(p) for p in ["pandas", "numpy", "huggingface_hub"]},
        "git_commit": e2.git("rev-parse", "HEAD"), "git_dirty": bool(e2.git("status", "--porcelain"))}, indent=2))
    print(res[(res.origin == "average")].pivot_table(index=["metric", "subset"], columns="variant", values="skill").round(4))
    for m, d in dec.items():
        print(f"{m}: {d['variant']}  ({d['reason']})")
    print("wrote", out)


if __name__ == "__main__":
    main()
