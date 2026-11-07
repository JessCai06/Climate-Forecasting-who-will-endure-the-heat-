"""Run the contest's starter code (random forest on 3 lags) and score it like the leaderboard
(live years 2019-2021). Scoring uses NOAA 2019-2021 observations (code/truth.py): ANALYSIS ONLY,
never a forecast input, and the forecast below is frozen before it is read.
Usage: python code/starter_score.py OBS_CSV   (OBS_CSV from code/fetch_truth.py)"""
import sys, calendar, warnings
import numpy as np, pandas as pd
from huggingface_hub import hf_hub_download
from sklearn.ensemble import RandomForestRegressor
sys.path.insert(0, __file__.rsplit("code", 1)[0] + "code")
from truth import annual_from_daily
warnings.filterwarnings("ignore")

REPO = "CMU-OSPO/protostar-climate-train-to-2018"
METRICS = {"annual_avg_temp": "Avg Temp", "total_precip_in": "ToT Prcp", "hottest_day_temp": "Max Tmax", "cdd": "cdd"}
LIVE = [2019, 2020, 2021]
HDR = ["Score", "Avg temp MAE °F", "Precip MAE in", "Hottest day MAE °F", "CDD MAE °F-days"]

# ---- 1. data (<= 2018) -------------------------------------------------------------------
train_df = pd.read_parquet(hf_hub_download(REPO, "annual_indices/train-00000-of-00001.parquet", repo_type="dataset"))
cov = pd.read_parquet(hf_hub_download(REPO, "coverage_and_stations/train-00000-of-00001.parquet", repo_type="dataset"))
assert train_df.Year.max() <= 2018
train_df = train_df.replace([np.inf, -np.inf], np.nan)  # Max Tmax is -inf in 1184 all-missing years; starter code would crash
train_df = train_df.sort_values(["ID", "Year"]).reset_index(drop=True)

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
    days = a.Year.map(lambda y: 366 if calendar.isleap(y) else 365)
    miss_both = days - a.merge(cov[["ID", "Year", "Days Both"]], on=["ID", "Year"], how="left")["Days Both"]
    v = {"annual_avg_temp": a[["Miss Tmax", "Miss Tmin"]].max(axis=1) <= 10, "total_precip_in": a["Miss Prcp"] <= 10,
         "hottest_day_temp": a["Miss Tmax"] <= 10, "cdd": miss_both <= 10}
    return {m: v[m] & a[c].notna() for m, c in METRICS.items()}

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

res = {k: score(v) for k, v in models.items()}
ref = res["30-year average"]
print(f"{'Model':<30}" + "".join(f"{h:>20}" for h in HDR))
for k, mae in res.items():
    S = np.mean([1 - mae[m] / ref[m] for m in METRICS])
    print(f"{k:<30}{100 * max(0, S):>20.1f}" + "".join(f"{mae[m]:>20.3f}" for m in METRICS))
print("\nLeaderboard reference '10-year mean · example notebook': 10.4  1.191  5.782  2.295  149.6")
