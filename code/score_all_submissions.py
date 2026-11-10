"""Score every frozen candidate forecast in outputs/ against NOAA observations: ANALYSIS ONLY.
Per metric MAE on 2019-2021, 2022-2025 and 2019-2025 (the final window), same validity rules and city filter as
starter_score.py. Never a forecast input and never used by the model code.
Run from the repo root:  python code/score_all_submissions.py   -> outputs/score_all/all_scores.csv"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shared import METRICS, load_train, valid_flags
from truth import annual_from_daily

ROOT = Path(__file__).resolve().parent.parent
train_df, cov = load_train()
flags = valid_flags(train_df, cov)
ok = {}
for m, col in METRICS.items():
    d = train_df.assign(v=train_df[col].where(flags[m]))
    for cid, g in d.groupby("ID"):
        s = g.set_index("Year")["v"].dropna()
        ok[(cid, m)] = len(s[s.index >= 1989]) >= 10

obs = pd.concat([pd.read_csv(ROOT / f, dtype={"DATE": str}) for f in ("obs_2018_2021.csv", "obs_2021_2025.csv")])
obs = obs.drop_duplicates(["ID", "DATE"])
truth = annual_from_daily(obs)
TV = {"annual_avg_temp": ("avg_temp", np.maximum(truth.miss_tmax, truth.miss_tmin)), "total_precip_in": ("tot_prcp", truth.miss_prcp),
      "hottest_day_temp": ("max_tmax", truth.miss_tmax), "cdd": ("cdd", truth.miss_both)}
WINDOWS = {"2019-2021": range(2019, 2022), "2022-2025": range(2022, 2026), "2019-2025": range(2019, 2026)}


def mae(fc, years, m):
    col, miss = TV[m]
    t = truth.assign(miss=miss)
    t = t[t.year.isin(years) & (t.miss <= 10) & t[col].notna()]
    return float(np.mean([abs(fc[(r.ID, m)][r.year - 2019] - getattr(r, col)) for r in t.itertuples()
                          if (r.ID, m) in fc and ok.get((r.ID, m))]))


def load(path):
    sub = pd.read_csv(path, dtype={"city_id": str})
    return {k: g.sort_values("year").predicted_value.tolist() for k, g in sub.groupby(["city_id", "metric"])}


files = sorted(p for p in (ROOT / "outputs").glob("*/submission*.csv"))
files += [ROOT / "submission.csv"]
rows = []
for p in files:
    fc = load(p)
    name = "SUBMITTED submission.csv" if p.name == "submission.csv" and p.parent == ROOT else f"{p.parent.name}/{p.stem.replace('submission_', '')}"
    for w, yrs in WINDOWS.items():
        for m in METRICS:
            rows.append({"candidate": name, "window": w, "metric": m, "mae": mae(fc, yrs, m)})
df = pd.DataFrame(rows)
out = ROOT / "outputs" / "score_all"
out.mkdir(exist_ok=True)
df.to_csv(out / "all_scores.csv", index=False)
print(len(files), "candidates scored")
