"""Experiment 2: plain average vs plain line vs line + random-forest hybrid (spec: exp02_line_forest_hybrid_spec.md).

Run from the repo root:   python code/exp02_line_forest.py [--charts]
Writes outputs/exp02/: heldout_results.csv, decision.json (BEFORE the final forecast),
submission_exp02.csv, run_log.json (+ charts/ with --charts).
Then score it (analysis only):  python code/starter_score.py obs_2018_2021.csv

Data rule: only data up to 2018 is read. Nothing here reads observations after 2018;
every choice is made on held-back years inside the training data.
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shared import METRICS, assert_cutoff, dataset_revision, load_train, valid_flags

ROOT = Path(__file__).resolve().parent.parent
SEED = 42
WINDOW = 30
ORIGINS = [1998, 2004, 2011]
H = 7
MIN_VALID = 10
MARGIN = 0.02          # hybrid must beat the better of line/average by 2 skill points
N_TREES = 100
# "decide" = choose among hybrid / line / average with the held-back rule in decide().
METRIC_PLAN = {"annual_avg_temp": "decide", "total_precip_in": "line", "cdd": "decide", "hottest_day_temp": "avg"}
CLIP0 = {"total_precip_in", "cdd"}   # these can never be negative
METHODS = ["avg", "line", "hybrid"]
EXP02_LABEL = "Line + average (exp02)"   # name of this experiment's row in the scorer table, charts and logs
LABEL = {"avg": "Plain average", "line": "Plain line", "hybrid": "Line + Forest hybrid"}


# ------------------------------------------------------------------ forecasting
def _window_series(d, v, origin):
    """{city: Series(valid values, index=year)} over the 30 years ending at `origin`."""
    lo = origin - WINDOW + 1
    m = d["Year"].between(lo, origin) & v.notna()
    return {c: g.set_index("Year")["v"] for c, g in d.loc[m].assign(v=v[m]).groupby("ID")}


def _line(s, years):
    slope, icpt = np.polyfit(s.index.values.astype(float), s.values, 1)
    return icpt + slope * np.asarray(years, float), slope, icpt


def make_forecast(train_df, cov, metric_plan, origin=2018):
    """Returns {(city_id, metric): [v(origin+1), ..., v(origin+7)]} (2019..2025 when origin=2018).
    metric_plan maps metric -> 'avg' | 'line' | 'hybrid' (resolve 'decide' first, see decide())."""
    assert_cutoff(train_df, "train_df")
    cities = sorted(train_df["ID"].unique())
    d = train_df[train_df["Year"] <= origin]
    flags = valid_flags(d, cov)
    years = np.arange(origin + 1, origin + H + 1)
    out = {}
    for metric, method in metric_plan.items():
        if method not in METHODS:
            raise ValueError(f"{metric}: method '{method}' unresolved")
        v = d[METRICS[metric]].where(flags[metric])
        ser = _window_series(d, v, origin)
        pooled = float(np.concatenate([s.values for s in ser.values()]).mean()) if ser else 0.0
        enough = {c for c, s in ser.items() if len(s) >= MIN_VALID}
        lo_clip = 0.0 if metric in CLIP0 else -np.inf

        fc = {}
        for c in cities:  # plain-average fallback: whatever valid years exist, else the cross-city mean
            fc[c] = np.full(H, float(ser[c].mean()) if c in ser else pooled)
        if method in ("line", "hybrid"):
            lines = {c: _line(ser[c], years) for c in enough}
            for c, (vals, _, _) in lines.items():
                fc[c] = vals
        if method == "hybrid" and enough:
            lw = np.arange(origin - WINDOW + 1, origin + 1)
            rows, last = [], {}
            for c in sorted(enough):
                _, slope, icpt = lines[c]
                resid = ser[c] - (icpt + slope * ser[c].index.values.astype(float))
                full = resid.reindex(lw)               # by year number: a missing year is NaN
                lag = pd.DataFrame({"y": full, **{f"lag_{k}": full.shift(k) for k in (1, 2, 3)}}).dropna()
                rows.append(lag)
                last[c] = (int(resid.index[-1]), list(resid.values[-3:]))
            tr = pd.concat(rows)
            feats = ["lag_1", "lag_2", "lag_3"]
            if len(tr):
                rf = RandomForestRegressor(n_estimators=N_TREES, random_state=SEED).fit(tr[feats], tr["y"])
                hist = {c: list(h) for c, (_, h) in last.items()}
                start = {c: L + 1 for c, (L, _) in last.items()}
                pred = {c: [] for c in last}
                for t in range(min(start.values()), origin + H + 1):   # step through gaps, one year at a time
                    act = [c for c in sorted(last) if start[c] <= t]
                    X = pd.DataFrame([hist[c][::-1][:3] for c in act], columns=feats)
                    for c, p in zip(act, rf.predict(X)):
                        hist[c].append(float(p))
                        if t > origin:
                            pred[c].append(float(p))
                for c in last:
                    fc[c] = lines[c][0] + np.array(pred[c][-H:])
        for c in cities:
            out[(c, metric)] = [float(x) for x in np.maximum(fc[c], lo_clip)]
    return out


# ---------------------------------------------------------------- held-back test
def heldout(train_df, cov, origins=ORIGINS):
    """MAE and skill (vs plain average) per metric, method and origin, pooled over scored city-years."""
    flags_all = valid_flags(train_df, cov)
    rows = []
    for o in origins:
        res = {m: make_forecast(train_df, cov, {k: m for k in METRICS}, o) for m in METHODS}
        for metric, col in METRICS.items():
            v = train_df[col].where(flags_all[metric])
            win = _window_series(train_df[train_df["Year"] <= o], v[train_df["Year"] <= o], o)
            ok = {c for c, s in win.items() if len(s) >= MIN_VALID}
            t = train_df.assign(v=v)[train_df["Year"].between(o + 1, o + H)].dropna(subset=["v"])
            t = t[t["ID"].isin(ok)]
            err = {m: [] for m in METHODS}
            for r in t.itertuples():
                for m in METHODS:
                    err[m].append(abs(res[m][(r.ID, metric)][r.Year - o - 1] - r.v))
            mae = {m: float(np.mean(err[m])) for m in METHODS}
            for m in METHODS:
                rows.append({"metric": metric, "method": m, "origin": o, "mae": mae[m],
                             "skill": 1 - mae[m] / mae["avg"], "n": len(err[m])})
    df = pd.DataFrame(rows)
    avg = df.groupby(["metric", "method"], sort=False)[["mae", "skill", "n"]].mean().reset_index()
    avg.insert(2, "origin", "average")
    return pd.concat([df.assign(origin=df.origin.astype(str)), avg], ignore_index=True)


def decide(res, plan=METRIC_PLAN, margin=MARGIN):
    """The decision rule of spec section 5. Returns {metric: {...numbers and chosen method...}}."""
    dec = {}
    for metric, how in plan.items():
        r = res[res.metric == metric]
        sk = {m: float(r[(r.method == m) & (r.origin == "average")].skill.iloc[0]) for m in METHODS}
        per = {m: {o: float(x) for o, x in zip(r[(r.method == m) & (r.origin != "average")].origin,
                                               r[(r.method == m) & (r.origin != "average")].skill)} for m in METHODS}
        info = {"plan": how, "avg_skill": sk, "per_origin_skill": per}
        if how == "decide":
            best_other = "line" if sk["line"] >= sk["avg"] else "avg"
            wins = sum(per["hybrid"][o] > per["line"][o] and per["hybrid"][o] > per["avg"][o] for o in per["hybrid"])
            checks = {"avg_skill_higher_than_line_and_avg": sk["hybrid"] > max(sk["line"], sk["avg"]),
                      "beats_both_in_at_least_2_of_3_origins": wins >= 2,
                      f"margin_ge_{margin}": sk["hybrid"] - max(sk["line"], sk["avg"]) >= margin}
            info.update(checks=checks, origins_won=wins, margin_achieved=sk["hybrid"] - max(sk["line"], sk["avg"]),
                        method="hybrid" if all(checks.values()) else best_other,
                        hybrid_dropped=not all(checks.values()))
        else:
            info["method"] = how
        dec[metric] = info
    return dec


# ------------------------------------------------------------------------ main
def git(*a):
    try:
        return subprocess.check_output(["git", *a], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


def to_rows(fc):
    return pd.DataFrame([{"city_id": c, "year": 2019 + i, "metric": m, "predicted_value": x}
                         for (c, m), vals in fc.items() for i, x in enumerate(vals)]
                        ).sort_values(["city_id", "year", "metric"]).reset_index(drop=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(ROOT / "outputs" / "exp02"))
    ap.add_argument("--charts", action="store_true", help="also draw the charts (code/exp02_charts.py)")
    a = ap.parse_args(argv)
    out = Path(a.out_dir)
    (out / "charts").mkdir(parents=True, exist_ok=True)

    train_df, cov = load_train()
    # 1. held-back test -> heldout_results.csv, then the decision -> decision.json (before any final forecast)
    res = heldout(train_df, cov)
    res.to_csv(out / "heldout_results.csv", index=False)
    dec = decide(res)
    (out / "decision.json").write_text(json.dumps(dec, indent=2))
    # 2. final forecast with the decided plan
    plan = {m: d["method"] for m, d in dec.items()}
    fc = make_forecast(train_df, cov, plan, 2018)
    sub = to_rows(fc)
    assert len(sub) == 210 * 7 * 4 and np.isfinite(sub.predicted_value).all()
    assert (sub[sub.metric.isin(CLIP0)].predicted_value >= 0).all()
    sub.to_csv(out / "submission_exp02.csv", index=False)
    (out / "run_log.json").write_text(json.dumps({
        "experiment": "exp02", "scorer_label": EXP02_LABEL, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "config": {"METRIC_PLAN": METRIC_PLAN, "resolved_plan": plan, "MARGIN": MARGIN, "WINDOW": WINDOW,
                   "ORIGINS": ORIGINS, "N_TREES": N_TREES, "SEED": SEED},
        "dataset": "CMU-OSPO/protostar-climate-train-to-2018", "dataset_revision": dataset_revision(),
        "packages": {p: version(p) for p in ["pandas", "numpy", "scikit-learn", "matplotlib", "huggingface_hub"]},
        "git_commit": git("rev-parse", "HEAD"), "git_dirty": bool(git("status", "--porcelain"))}, indent=2))

    show = res[res.origin == "average"].pivot(index="metric", columns="method", values="skill")
    print("Held-back average skill (vs plain average):\n", show.round(3).to_string())
    for m, d in dec.items():
        print(f"{m}: {d['method']}" + (" (hybrid dropped)" if d.get("hybrid_dropped") else ""))
    print("wrote", out)
    if a.charts:
        from exp02_charts import make_charts
        make_charts(out, train_df, cov)


if __name__ == "__main__":
    main()
