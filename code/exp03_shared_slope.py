"""Experiment 3: make the trend line less noisy.
Ideas per metric: A plain average, B own line, C shared slope (one slope for all cities),
D half slope (own slope x 0.5). Chosen per metric by a held-back test on past years only.

Run from the repo root:   python code/exp03_shared_slope.py [--charts]
Writes outputs/exp03/: heldout_results.csv, decision.json (BEFORE the final forecast),
submission_exp03.csv (chosen), submission_exp03_shared_all.csv, submission_exp03_half_all.csv, run_log.json.
Score it (analysis only):  python code/starter_score.py obs_2018_2021.csv

Data rule: only data up to 2018 is read; this module never reads observation/truth files.
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
import exp02_line_forest as e2   # reuse: windows, line fit, fallbacks, constants (exp02 itself is unchanged)

ROOT = e2.ROOT
H, WINDOW, MIN_VALID, SEED, ORIGINS, CLIP0 = e2.H, e2.WINDOW, e2.MIN_VALID, e2.SEED, e2.ORIGINS, e2.CLIP0
HALF = 0.5                    # fixed; no other factor is tried
CLOSE = 0.01                  # winner must lead the runner-up by at least this much skill
METHODS = ["avg", "line", "shared", "half"]          # ideas A, B, C, D
SIMPLICITY = ["avg", "line", "half", "shared"]       # A, B, D, C (simplest first)
LABEL = {"avg": "A Plain average", "line": "B Own line", "shared": "C Shared slope", "half": "D Half slope"}
EXP03_LABEL = "Exp03 chosen per metric"


def make_forecast(train_df, cov, metric_plan, origin=2018):
    """Returns {(city_id, metric): [v(origin+1) .. v(origin+7)]}; metric_plan maps metric -> one of METHODS.
    Pivot for C and D: forecast = city_mean + slope * (year - city_mean_year) over the 30-year window."""
    assert_cutoff(train_df, "train_df")
    cities = sorted(train_df["ID"].unique())
    d = train_df[train_df["Year"] <= origin]
    flags = valid_flags(d, cov)
    years = np.arange(origin + 1, origin + H + 1, dtype=float)
    # A and B come from exp02's code so the shared parts (fallbacks, clipping) stay identical
    base = e2.make_forecast(train_df, cov, {m: ("avg" if p == "avg" else "line") for m, p in metric_plan.items()}, origin)
    out = {}
    for metric, method in metric_plan.items():
        if method not in METHODS:
            raise ValueError(f"{metric}: method '{method}' unknown")
        if method in ("avg", "line"):
            out.update({k: v for k, v in base.items() if k[1] == metric})
            continue
        v = d[METRICS[metric]].where(flags[metric])
        ser = e2._window_series(d, v, origin)
        enough = sorted(c for c, s in ser.items() if len(s) >= MIN_VALID)
        piv = {c: (float(ser[c].index.values.mean()), float(ser[c].values.mean())) for c in enough}
        own = {c: e2._line(ser[c], years)[1] for c in enough}
        if method == "shared":   # least-squares slope through all demeaned points together
            xs = np.concatenate([ser[c].index.values - piv[c][0] for c in enough])
            ys = np.concatenate([ser[c].values - piv[c][1] for c in enough])
            shared = float((xs * ys).sum() / (xs * xs).sum())
        lo = 0.0 if metric in CLIP0 else -np.inf
        for c in cities:
            if c in piv:
                slope = shared if method == "shared" else HALF * own[c]
                vals = piv[c][1] + slope * (years - piv[c][0])
                out[(c, metric)] = [float(x) for x in np.maximum(vals, lo)]
            else:   # fewer than 10 valid years: exp02's plain-average fallback
                out[(c, metric)] = base[(c, metric)]
    return out


# ---------------------------------------------------------------- held-back test
def heldout(train_df, cov, origins=ORIGINS):
    flags_all = valid_flags(train_df, cov)
    rows = []
    for o in origins:
        res = {m: make_forecast(train_df, cov, {k: m for k in METRICS}, o) for m in METHODS}
        past = train_df["Year"] <= o
        for metric, col in METRICS.items():
            v = train_df[col].where(flags_all[metric])
            win = e2._window_series(train_df[past], v[past], o)
            ok = {c for c, s in win.items() if len(s) >= MIN_VALID}
            t = train_df.assign(v=v)[train_df["Year"].between(o + 1, o + H)].dropna(subset=["v"])
            t = t[t["ID"].isin(ok)]
            err = {m: [abs(res[m][(r.ID, metric)][r.Year - o - 1] - r.v) for r in t.itertuples()] for m in METHODS}
            mae = {m: float(np.mean(err[m])) for m in METHODS}
            for m in METHODS:
                rows.append({"metric": metric, "method": m, "origin": str(o), "mae": mae[m],
                             "skill": 1 - mae[m] / mae["avg"], "n": len(err[m])})
    df = pd.DataFrame(rows)
    avg = df.groupby(["metric", "method"], sort=False)[["mae", "skill", "n"]].mean().reset_index()
    avg.insert(2, "origin", "average")
    return pd.concat([df, avg], ignore_index=True)


def decide(res):
    """1) highest average skill; 2) must beat the plain average in >=2 of 3 origins, else A;
    3) if it leads the second best by < CLOSE, take the simpler of the two (A, B, D, C).
    Interpretation: the simpler pick in step 3 must also pass step 2, otherwise A."""
    dec = {}
    for metric in METRICS:
        r = res[res.metric == metric]
        sk = {m: float(r[(r.method == m) & (r.origin == "average")].skill.iloc[0]) for m in METHODS}
        per = {m: {o: float(x) for o, x in zip(r[(r.method == m) & (r.origin != "average")].origin,
                                               r[(r.method == m) & (r.origin != "average")].skill)} for m in METHODS}
        beats = {m: sum(per[m][o] > 0 for o in per[m]) for m in METHODS}   # origins beating the plain average
        ranked = sorted(METHODS, key=lambda m: (-sk[m], SIMPLICITY.index(m)))
        winner, second = ranked[0], ranked[1]
        lead = sk[winner] - sk[second]
        info = {"avg_skill": sk, "per_origin_skill": per, "origins_beating_plain_average": beats,
                "ranked_by_avg_skill": ranked, "highest": winner, "runner_up": second, "lead_over_runner_up": lead}
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
    ap.add_argument("--out-dir", default=str(ROOT / "outputs" / "exp03"))
    ap.add_argument("--charts", action="store_true")
    a = ap.parse_args(argv)
    out = Path(a.out_dir)
    (out / "charts").mkdir(parents=True, exist_ok=True)

    train_df, cov = load_train()
    res = heldout(train_df, cov)
    res.to_csv(out / "heldout_results.csv", index=False)
    dec = decide(res)
    (out / "decision.json").write_text(json.dumps(dec, indent=2))          # before any final forecast
    plan = {m: d["method"] for m, d in dec.items()}
    for name, p in (("submission_exp03.csv", plan),
                    ("submission_exp03_shared_all.csv", {m: "shared" for m in METRICS}),
                    ("submission_exp03_half_all.csv", {m: "half" for m in METRICS})):
        sub = e2.to_rows(make_forecast(train_df, cov, p, 2018))
        assert len(sub) == 210 * 7 * 4 and np.isfinite(sub.predicted_value).all()
        assert (sub[sub.metric.isin(CLIP0)].predicted_value >= 0).all()
        sub.to_csv(out / name, index=False)
    (out / "run_log.json").write_text(json.dumps({
        "experiment": "exp03", "scorer_labels": [EXP03_LABEL, "Shared slope (all metrics)", "Half slope (all metrics)"],
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "config": {"METHODS": METHODS, "SIMPLICITY": SIMPLICITY, "HALF": HALF, "CLOSE": CLOSE, "WINDOW": WINDOW,
                   "ORIGINS": ORIGINS, "SEED": SEED, "resolved_plan": plan},
        "dataset": e2.__dict__.get("REPO", "CMU-OSPO/protostar-climate-train-to-2018"), "dataset_revision": dataset_revision(),
        "packages": {p: version(p) for p in ["pandas", "numpy", "scikit-learn", "matplotlib", "huggingface_hub"]},
        "git_commit": e2.git("rev-parse", "HEAD"), "git_dirty": bool(e2.git("status", "--porcelain"))}, indent=2))
    for m, d in dec.items():
        print(f"{m}: {d['method']}  ({d['reason']})")
    print("wrote", out)
    if a.charts:
        from exp03_charts import make_charts
        make_charts(out, train_df, cov)


if __name__ == "__main__":
    main()
