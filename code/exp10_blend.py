"""Experiment 10: weighted blend of the candidates Experiments 5 and 5B already built.

Rule (written first): docs/exp10_blend_rule.md. Per metric, weights are non-negative, sum to 1, on a 0.1 grid,
fitted to minimise the mean over held-back origins of (blend MAE / plain-average MAE). A leave-one-origin-out
test gives the blend's honest skill; the blend replaces the Experiment 5B pick for a metric only if it beats that
pick by >= 0.01 average skill and wins in >= 2 of 3 left-out origins.

Run from the repo root:   python code/exp10_blend.py
Writes outputs/exp10/: heldout_results.csv, weights.json, decision.json (BEFORE the final forecast),
submission_exp10.csv, run_log.json.

Data rule: only data up to 2018 is read (shared.load_train guards it). No 2019-2025 value is used.
"""
import itertools
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
ORIGINS, H, MIN_VALID = e2.ORIGINS, e2.H, e2.MIN_VALID
STEP, MARGIN = 0.1, 0.01
COMMON = ["avg", "r10", "r15", "shared", "r10s", "r15s"]
POOL = {"annual_avg_temp": COMMON + ["stn"],
        "total_precip_in": COMMON,
        "hottest_day_temp": COMMON + ["h30p95", "h15p95"],
        "cdd": ["shared", "r10s", "r15s", "scaled", "r15sc", "cdd10d", "cdd15d"]}
CURRENT = {"annual_avg_temp": "r15s", "total_precip_in": "avg", "hottest_day_temp": "avg", "cdd": "cdd10d"}


def grid(k):
    """All weight vectors of length k, multiples of STEP, summing to 1."""
    n = round(1 / STEP)
    rows = [c for c in itertools.product(range(n + 1), repeat=k - 1) if sum(c) <= n]
    return np.array([list(c) + [n - sum(c)] for c in rows], float) / n


def collect(train_df, cov, daily, days):
    """Per origin and metric: prediction matrix (rows = scored city-years, cols = pool) and truth."""
    flags_all = valid_flags(train_df, cov)
    data = {}
    for o in ORIGINS:
        res = e5.make_all(train_df, cov, o)
        new, _ = e5b.make_new(train_df, cov, daily, days, o)
        res.update(new)
        past = train_df["Year"] <= o
        for metric, col in METRICS.items():
            v = train_df[col].where(flags_all[metric])
            win = e2._window_series(train_df[past], v[past], o)
            ok = {c for c, s in win.items() if len(s) >= MIN_VALID}
            t = train_df.assign(v=v)[train_df["Year"].between(o + 1, o + H)].dropna(subset=["v"])
            t = t[t["ID"].isin(ok)]
            P = np.array([[res[m][(r.ID, metric)][r.Year - o - 1] for m in POOL[metric]] for r in t.itertuples()])
            avg = np.array([res["avg"][(r.ID, metric)][r.Year - o - 1] for r in t.itertuples()])
            data[(o, metric)] = (P, t["v"].to_numpy(float), avg)
    return data


def ratio(P, y, avg, W):
    """Per weight vector: blend MAE / plain-average MAE on one origin."""
    return np.abs(P @ W.T - y[:, None]).mean(axis=0) / np.abs(avg - y).mean()


def fit(data, metric, origins, W):
    r = np.mean([ratio(*data[(o, metric)], W) for o in origins], axis=0)
    return W[int(np.argmin(r))]


def evaluate(data):
    rows, weights, dec = [], {}, {}
    for metric in METRICS:
        W = grid(len(POOL[metric]))
        cur_i = POOL[metric].index(CURRENT[metric]) if CURRENT[metric] in POOL[metric] else None
        out = {}
        for o in ORIGINS:
            P, y, avg = data[(o, metric)]
            w = fit(data, metric, [x for x in ORIGINS if x != o], W)
            blend_skill = 1 - float(ratio(P, y, avg, w[None, :])[0])
            if cur_i is not None:
                cw = np.zeros(len(POOL[metric]))
                cw[cur_i] = 1
                cur_skill = 1 - float(ratio(P, y, avg, cw[None, :])[0])
            else:   # current method outside the pool: score it separately below
                cur_skill = np.nan
            out[o] = (blend_skill, cur_skill, w)
            rows.append({"metric": metric, "origin": o, "blend_loo_skill": blend_skill, "current_skill": cur_skill})
        weights[metric] = dict(zip(POOL[metric], fit(data, metric, ORIGINS, W).round(2).tolist()))
        dec[metric] = {"pool": POOL[metric], "current": CURRENT[metric], "final_weights": weights[metric],
                       "loo": {str(o): {"blend": out[o][0], "current": out[o][1],
                                        "weights": dict(zip(POOL[metric], out[o][2].round(2).tolist()))} for o in ORIGINS}}
    return rows, weights, dec


def main():
    out = ROOT / "outputs" / "exp10"
    out.mkdir(parents=True, exist_ok=True)
    train_df, cov = load_train()
    daily = e5b.load_daily()
    days = e5b.daily_by_city_year(daily)
    data = collect(train_df, cov, daily, days)

    # current-method skill per origin, scored the same way (cdd10d is in the cdd pool only via cdd10d)
    rows, weights, dec = evaluate(data)
    for metric in METRICS:
        d = dec[metric]
        bl = [d["loo"][str(o)]["blend"] for o in ORIGINS]
        cu = [d["loo"][str(o)]["current"] for o in ORIGINS]
        d["blend_avg_skill"], d["current_avg_skill"] = float(np.mean(bl)), float(np.mean(cu))
        d["origins_blend_wins"] = int(sum(b > c for b, c in zip(bl, cu)))
        d["lead"] = d["blend_avg_skill"] - d["current_avg_skill"]
        ok = d["lead"] >= MARGIN and d["origins_blend_wins"] >= 2
        d["use_blend"] = bool(ok)
        d["method"] = "blend" if ok else d["current"]
        d["reason"] = (f"blend {d['blend_avg_skill']:.4f} vs {d['current']} {d['current_avg_skill']:.4f} "
                       f"(lead {d['lead']:+.4f}, wins {d['origins_blend_wins']}/3): " + ("blend used" if ok else "current kept"))
    pd.DataFrame(rows).to_csv(out / "heldout_results.csv", index=False)
    (out / "weights.json").write_text(json.dumps(weights, indent=2))
    (out / "decision.json").write_text(json.dumps(dec, indent=2))        # before the final forecast

    final = e5.make_all(train_df, cov, 2018)
    new, _ = e5b.make_new(train_df, cov, daily, days, 2018)
    final.update(new)
    chosen = {}
    for k in final["avg"]:
        metric = k[1]
        if dec[metric]["use_blend"]:
            w = weights[metric]
            chosen[k] = [float(x) for x in sum(w[m] * np.array(final[m][k]) for m in POOL[metric])]
        else:
            chosen[k] = final[CURRENT[metric]][k]
    sub = e2.to_rows(chosen)
    assert len(sub) == 210 * 7 * 4 and np.isfinite(sub.predicted_value).all()
    assert (sub[sub.metric.isin(e2.CLIP0)].predicted_value >= 0).all()
    sub.to_csv(out / "submission_exp10.csv", index=False)
    # the blend for every metric regardless of the rule, for analysis only
    allb = {k: [float(x) for x in sum(weights[k[1]][m] * np.array(final[m][k]) for m in POOL[k[1]])] for k in final["avg"]}
    e2.to_rows(allb).to_csv(out / "submission_exp10_blend_all.csv", index=False)
    (out / "run_log.json").write_text(json.dumps({
        "experiment": "exp10", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "config": {"POOL": POOL, "CURRENT": CURRENT, "STEP": STEP, "MARGIN": MARGIN, "ORIGINS": ORIGINS},
        "dataset": REPO, "dataset_revision": dataset_revision(),
        "packages": {p: version(p) for p in ["pandas", "numpy", "huggingface_hub"]},
        "git_commit": e2.git("rev-parse", "HEAD"), "git_dirty": bool(e2.git("status", "--porcelain"))}, indent=2))
    for m, d in dec.items():
        print(f"{m}: {d['reason']}\n   weights {d['final_weights']}")


if __name__ == "__main__":
    main()
