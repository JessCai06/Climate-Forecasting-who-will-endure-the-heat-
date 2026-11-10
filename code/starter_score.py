"""Run the contest's starter code (random forest on 3 lags) and score it like the leaderboard
(live years 2019-2021). Scoring uses NOAA 2019-2021 observations (code/truth.py): ANALYSIS ONLY,
never a forecast input, and the forecast below is frozen before it is read.
Usage: python code/starter_score.py OBS_CSV [FIRST-LAST]   (OBS_CSV from code/fetch_truth.py;
years default to the live window 2019-2021, e.g. 2022-2025 previews the final window)"""
import sys, warnings
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestRegressor
sys.path.insert(0, str(Path(__file__).resolve().parent))
from truth import annual_from_daily
from shared import METRICS, load_train, valid_flags as _valid_flags
warnings.filterwarnings("ignore")

LIVE = (list(range(int(sys.argv[2].split("-")[0]), int(sys.argv[2].split("-")[1]) + 1))
        if len(sys.argv) > 2 else [2019, 2020, 2021])
HDR = ["Score", "Avg temp MAE °F", "Precip MAE in", "Hottest day MAE °F", "CDD MAE °F-days"]
EXP02_SUBMISSION = Path(__file__).resolve().parent.parent / "outputs" / "exp02" / "submission_exp02.csv"

# ---- 1. data (<= 2018, cutoff guard, inf -> NaN: see shared.py) --------------------------
train_df, cov = load_train()

# ---- 2/3. starter code: lag features + RandomForest, iterative 2019-2025 ----------------
def starter_forecast(target):
    df = train_df[["ID", "Year", target]].copy()
    for k in (1, 2, 3):
        df[f"lag_{k}"] = df.groupby("ID")[target].shift(k)
    features = ["lag_1", "lag_2", "lag_3"]
    fit_df = df.dropna(subset=features + [target])
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(fit_df[features], fit_df[target])
    out = {}
    for cid, g in df.groupby("ID"):
        hist = list(g[target].ffill().values[-3:])  # ffill: a few cities end 2018 with a missing value
        preds = []
        for _ in range(7):
            p = float(model.predict(pd.DataFrame([hist[::-1][:3]], columns=features))[0])
            preds.append(p); hist.append(p)
        out[cid] = preds
    return out

# ---- baselines (official definitions + the leaderboard's 10-year mean) -----------------
def valid_flags(a):
    return _valid_flags(a, cov)

flags = valid_flags(train_df)
base = {k: {} for k in ("30-year average", "10-year mean", "last year repeated", "linear trend")}
baseline_ok = {}
for m, col in METRICS.items():
    d = train_df.assign(v=train_df[col].where(flags[m]))
    for cid, g in d.groupby("ID"):
        s = g.set_index("Year")["v"].dropna()
        w = s[s.index >= 1989]
        baseline_ok[(cid, m)] = len(w) >= 10
        if len(w) == 0: continue
        slope, icpt = np.polyfit(w.index.values.astype(float), w.values, 1) if len(w) > 1 else (0, w.mean())
        base["30-year average"][(cid, m)] = np.full(7, w.mean())
        base["10-year mean"][(cid, m)] = np.full(7, s[s.index >= 2009].mean())
        base["last year repeated"][(cid, m)] = np.full(7, s.iloc[-1])
        base["linear trend"][(cid, m)] = icpt + slope * np.arange(2019, 2026)

# ---- truth (NOAA 2019-2021, analysis only) ----------------------------------------------
obs = pd.read_csv(sys.argv[1], dtype={"DATE": str})
truth = annual_from_daily(obs)
tv = {"annual_avg_temp": ("avg_temp", np.maximum(truth.miss_tmax, truth.miss_tmin)), "total_precip_in": ("tot_prcp", truth.miss_prcp),
      "hottest_day_temp": ("max_tmax", truth.miss_tmax), "cdd": ("cdd", truth.miss_both)}
truth = truth[truth.year.isin(LIVE)]

def score(fc):  # fc[(cid, metric)] -> 7 values for 2019..2025
    mae = {}
    for m, (col, miss) in tv.items():
        t = truth.assign(miss=miss.loc[truth.index])
        t = t[(t.miss <= 10) & t[col].notna()]
        errs = [abs(fc[(r.ID, m)][r.year - 2019] - getattr(r, col)) for r in t.itertuples()
                if (r.ID, m) in fc and baseline_ok.get((r.ID, m))]
        mae[m] = float(np.mean(errs))
    return mae

models = {"Starter code (RandomForest)": {}}
for target_m, col in METRICS.items():
    for cid, p in starter_forecast(col).items():
        models["Starter code (RandomForest)"][(cid, target_m)] = p
models.update(base)
OUT = Path(__file__).resolve().parent.parent / "outputs"
for label, path in [("Line + average (exp02)", EXP02_SUBMISSION),  # frozen forecasts written earlier by the experiments
                    ("Exp03 chosen per metric (analysis only)", OUT / "exp03" / "submission_exp03.csv"),
                    ("Shared slope (all metrics) (analysis only)", OUT / "exp03" / "submission_exp03_shared_all.csv"),
                    ("Half slope (all metrics) (analysis only)", OUT / "exp03" / "submission_exp03_half_all.csv"),
                        ("Exp04 chosen per metric (analysis only)", OUT / "exp04" / "submission_exp04.csv"),
                        ("Regional slope 500 km (all) (analysis only)", OUT / "exp04" / "submission_exp04_reg500_all.csv"),
                        ("Regional slope 1000 km (all) (analysis only)", OUT / "exp04" / "submission_exp04_reg1000_all.csv"),
                        ("Best slope + filled gaps (analysis only)", OUT / "exp04" / "submission_exp04_filled_all.csv"),
                        ("Exp05 chosen per metric (analysis only)", OUT / "exp05" / "submission_exp05.csv"),
                        ("Exp06 chosen per metric (analysis only)", OUT / "exp06" / "submission_exp06.csv"),
                        ("Exp05B chosen per metric (analysis only)", OUT / "exp05b" / "submission_exp05b.csv"),
                        ("Exp05B cdd 15-yr delta (analysis only)", OUT / "exp05b" / "submission_exp05b_cdd15d.csv"),
                        ("Exp10 chosen per metric (analysis only)", OUT / "exp10" / "submission_exp10.csv"),
                        ("Exp10 weighted blend, all metrics (analysis only)", OUT / "exp10" / "submission_exp10_blend_all.csv")]:
    if path.exists():
        sub = pd.read_csv(path, dtype={"city_id": str})
        models[label] = {k: g.sort_values("year").predicted_value.tolist() for k, g in sub.groupby(["city_id", "metric"])}

res = {k: score(v) for k, v in models.items()}
ref = res["30-year average"]
print(f"{'Model':<44}" + "".join(f"{h:>20}" for h in HDR))
for k, mae in res.items():
    S = np.mean([1 - mae[m] / ref[m] for m in METRICS])
    print(f"{k:<44}{100 * max(0, S):>20.1f}" + "".join(f"{mae[m]:>20.3f}" for m in METRICS))
print("\nLeaderboard reference '10-year mean · example notebook': 10.4  1.191  5.782  2.295  149.6")
