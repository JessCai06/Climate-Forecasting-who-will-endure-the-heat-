"""Experiment 5: better levels and better slopes.

Exp03 forecasts temperature and cdd as `30-year mean + one shared slope x (year - mean year)`.
Exp05 tests three fixes to that, each chosen per metric on held-back past years only:

  1. Recent level (Optimal Climate Normals, Huang, van den Dool & Barnston 1996, J. Climate 9:809-817):
     use the mean of the city's last K valid years (K = 10 or 15, the two OCN values) instead of 30.
  2. Station-aware level: if the city's record switched stations inside the 30-year window, use only
     the years at its latest station (when there are >= 10 valid ones), since a move can shift the level.
  3. Scaled cdd slope: one shared slope gives Seattle and Miami the same cdd rise per year. Instead,
     cdd slope of city c = shared temperature slope x (cdd change per 1 F of annual temperature in c),
     the second factor fitted on the city's own past years.
  plus an equal-weight ensemble of the non-baseline candidates.

Candidates per metric (all fixed before any run):
  avg     30-year mean (A, the reference)             r10 / r15   mean of the last 10 / 15 valid years
  shared  30-year mean + shared slope (exp03's C)     r10s / r15s recent level + shared slope
  stn     station-aware level + shared slope          scaled      30-year mean + scaled slope (cdd only)
  r15sc   15-year level + scaled slope (cdd only)     ens         mean of every non-baseline candidate
Decision rule: exp03's, unchanged (highest average skill over origins 1998/2004/2011; must beat the plain
average in >= 2 of 3 origins; a lead under 0.01 over the runner-up goes to the simpler of the two).

Run from the repo root:   python code/exp05_levels_slopes.py
Writes outputs/exp05/: heldout_results.csv, decision.json (BEFORE the final forecast), submission_exp05.csv,
candidate forecasts submission_exp05_<method>_all.csv, run_log.json.

Data rule: only data up to 2018 is read (shared.load_train guards it); this module never reads
observation/truth files, and no choice here uses any 2019-2025 value.
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
import exp02_line_forest as e2   # reuse: window helper, plain-average fallbacks, row writer, git helper

ROOT = e2.ROOT
H, WINDOW, MIN_VALID, SEED, ORIGINS, CLIP0 = e2.H, e2.WINDOW, e2.MIN_VALID, e2.SEED, e2.ORIGINS, e2.CLIP0
CLOSE = 0.01
RECENT = (10, 15)                                    # OCN window lengths; no other values are tried
COMMON = ["avg", "r10", "r15", "shared", "stn", "r10s", "r15s"]
CDD_ONLY = ["scaled", "r15sc"]
CANDIDATES = {m: COMMON + (CDD_ONLY if m == "cdd" else []) + ["ens"] for m in METRICS}
SIMPLICITY = ["avg", "r10", "r15", "shared", "stn", "r10s", "r15s", "scaled", "r15sc", "ens"]  # simplest first
LABEL = {"avg": "A Plain average", "r10": "Recent 10-yr mean", "r15": "Recent 15-yr mean",
         "shared": "C Shared slope (exp03)", "stn": "Station-aware level + shared slope",
         "r10s": "Recent 10-yr level + shared slope", "r15s": "Recent 15-yr level + shared slope",
         "scaled": "30-yr level + scaled cdd slope", "r15sc": "Recent 15-yr level + scaled cdd slope",
         "ens": "Ensemble mean of non-baseline candidates"}
EXP05_LABEL = "Exp05 chosen per metric"


def _shared_slope(ser, cities):
    """Least-squares slope through every city's demeaned (year, value) points: exp03's idea C."""
    xs = np.concatenate([ser[c].index.values - ser[c].index.values.mean() for c in cities])
    ys = np.concatenate([ser[c].values - ser[c].values.mean() for c in cities])
    return float((xs * ys).sum() / (xs * xs).sum())


def _segment_years(seg, city, s):
    """Valid years of series `s` recorded at the city's latest station segment."""
    g = seg.get(city)
    if g is None:
        return s
    latest = g.reindex(s.index).dropna()
    if latest.empty:
        return s
    keep = latest.index[latest == latest.iloc[-1]]
    return s.loc[keep]


def make_all(train_df, cov, origin=2018):
    """Every candidate for every metric: {method: {(city_id, metric): [7 floats]}}."""
    assert_cutoff(train_df, "train_df")
    assert_cutoff(cov, "cov")
    cities = sorted(train_df["ID"].unique())
    d = train_df[train_df["Year"] <= origin]
    flags = valid_flags(d, cov)
    years = np.arange(origin + 1, origin + H + 1, dtype=float)
    base = e2.make_forecast(train_df, cov, {m: "avg" for m in METRICS}, origin)   # A + all fallbacks
    seg = {c: g.set_index("Year")["Station Segment"] for c, g in cov[cov["Year"] <= origin].groupby("ID")}

    ser = {}
    for metric, col in METRICS.items():
        ser[metric] = e2._window_series(d, d[col].where(flags[metric]), origin)
    enough = {m: sorted(c for c, s in ser[m].items() if len(s) >= MIN_VALID) for m in METRICS}
    slope = {m: _shared_slope(ser[m], enough[m]) for m in METRICS}

    # cdd sensitivity per city: OLS slope of cdd on Avg Temp over years where both are valid
    sens = {}
    t_ser, c_ser = ser["annual_avg_temp"], ser["cdd"]
    for c in enough["cdd"]:
        if c in t_ser:
            j = c_ser[c].index.intersection(t_ser[c].index)
            if len(j) >= MIN_VALID and np.ptp(t_ser[c].loc[j].values) > 0:
                sens[c] = float(np.polyfit(t_ser[c].loc[j].values, c_ser[c].loc[j].values, 1)[0])

    out = {m: {} for m in SIMPLICITY}
    for metric in METRICS:
        lo = 0.0 if metric in CLIP0 else -np.inf
        for c in cities:
            key = (c, metric)
            fallback = base[key]
            s = ser[metric].get(c)
            if c not in enough[metric]:
                for m in CANDIDATES[metric]:
                    out[m][key] = list(fallback)
                continue

            def level(sub):
                return float(sub.values.mean()), float(sub.index.values.mean())

            def path(lv, piv, b):
                return [float(x) for x in np.maximum(lv + b * (years - piv), lo)]

            full = level(s)
            rec = {k: level(s.iloc[-k:]) for k in RECENT}
            st = _segment_years(seg, c, s)
            stn = level(st) if len(st) >= MIN_VALID else full
            b = slope[metric]
            out["avg"][key] = list(fallback)
            out["r10"][key] = path(*rec[10], 0.0)
            out["r15"][key] = path(*rec[15], 0.0)
            out["shared"][key] = path(*full, b)
            out["stn"][key] = path(*stn, b)
            out["r10s"][key] = path(*rec[10], b)
            out["r15s"][key] = path(*rec[15], b)
            if metric == "cdd":
                bc = sens[c] * slope["annual_avg_temp"] if c in sens else b
                out["scaled"][key] = path(*full, bc)
                out["r15sc"][key] = path(*rec[15], bc)
            members = [m for m in CANDIDATES[metric] if m not in ("avg", "ens")]
            out["ens"][key] = [float(x) for x in np.mean([out[m][key] for m in members], axis=0)]
    return out


# ---------------------------------------------------------------- held-back test
def heldout(train_df, cov, origins=ORIGINS):
    """Same scoring as exp03: pooled MAE over valid city-years of cities with >= 10 valid window years."""
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


def decide(res, candidates=None, simplicity=None, label=None):
    """exp03's rule, over this metric's candidates (exp06 passes its own candidate set)."""
    CANDIDATES_, SIMPLICITY_, LABEL_ = candidates or CANDIDATES, simplicity or SIMPLICITY, label or LABEL
    dec = {}
    for metric in METRICS:
        cands = CANDIDATES_[metric]
        r = res[res.metric == metric]
        sk = {m: float(r[(r.method == m) & (r.origin == "average")].skill.iloc[0]) for m in cands}
        per = {m: dict(zip(r[(r.method == m) & (r.origin != "average")].origin,
                           r[(r.method == m) & (r.origin != "average")].skill.astype(float))) for m in cands}
        beats = {m: sum(x > 0 for x in per[m].values()) for m in cands}
        ranked = sorted(cands, key=lambda m: (-sk[m], SIMPLICITY_.index(m)))
        winner, second = ranked[0], ranked[1]
        lead = sk[winner] - sk[second]
        pick, why = winner, f"{LABEL_[winner]} has the highest average skill"
        if lead < CLOSE:
            simpler = min((winner, second), key=SIMPLICITY_.index)
            if simpler != winner:
                pick, why = simpler, f"rule 3: lead of {lead:.4f} over {LABEL_[second]} is under {CLOSE}, so the simpler idea wins"
        if pick != "avg" and beats[pick] < 2:
            why += f"; but {LABEL_[pick]} beat the plain average in only {beats[pick]} of 3 origins (rule 2)"
            pick = "avg"
        dec[metric] = {"avg_skill": sk, "per_origin_skill": per, "origins_beating_plain_average": beats,
                       "ranked_by_avg_skill": ranked, "highest": winner, "runner_up": second,
                       "lead_over_runner_up": lead, "method": pick, "reason": why}
    return dec


def to_rows(fc):
    return e2.to_rows(fc)


# ------------------------------------------------------------------------ main
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(ROOT / "outputs" / "exp05"))
    a = ap.parse_args(argv)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    train_df, cov = load_train()
    res = heldout(train_df, cov)
    res.to_csv(out / "heldout_results.csv", index=False)
    dec = decide(res)
    (out / "decision.json").write_text(json.dumps(dec, indent=2))          # before any final forecast

    final = make_all(train_df, cov, 2018)
    plan = {m: d["method"] for m, d in dec.items()}
    chosen = {k: v for metric, meth in plan.items() for k, v in final[meth].items() if k[1] == metric}
    files = {"submission_exp05.csv": chosen}
    for m in SIMPLICITY:   # each candidate for every metric it applies to (avg elsewhere), for analysis
        files[f"submission_exp05_{m}_all.csv"] = {k: (final[m] if k[1] in [x for x in METRICS if m in CANDIDATES[x]]
                                                     else final["avg"])[k] for k in final["avg"]}
    for name, fc in files.items():
        sub = to_rows(fc)
        assert len(sub) == 210 * 7 * 4 and np.isfinite(sub.predicted_value).all()
        assert (sub[sub.metric.isin(CLIP0)].predicted_value >= 0).all()
        sub.to_csv(out / name, index=False)
    (out / "run_log.json").write_text(json.dumps({
        "experiment": "exp05", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "config": {"CANDIDATES": CANDIDATES, "SIMPLICITY": SIMPLICITY, "RECENT": RECENT, "CLOSE": CLOSE,
                   "WINDOW": WINDOW, "ORIGINS": ORIGINS, "MIN_VALID": MIN_VALID, "resolved_plan": plan},
        "dataset": "CMU-OSPO/protostar-climate-train-to-2018", "dataset_revision": dataset_revision(),
        "packages": {p: version(p) for p in ["pandas", "numpy", "scikit-learn", "huggingface_hub"]},
        "git_commit": e2.git("rev-parse", "HEAD"), "git_dirty": bool(e2.git("status", "--porcelain"))}, indent=2))
    for m, d in dec.items():
        print(f"{m}: {d['method']}  ({d['reason']})")
    print("wrote", out)


if __name__ == "__main__":
    main()
