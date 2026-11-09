"""Helpers shared by the scorer and the experiments: data loading, cutoff guard, validity rules.
Reads only pre-2019 training data. Never touches truth/observation files."""
import calendar

import numpy as np
import pandas as pd
from huggingface_hub import HfApi, hf_hub_download

REPO = "CMU-OSPO/protostar-climate-train-to-2018"
CUTOFF_YEAR = 2018
METRICS = {"annual_avg_temp": "Avg Temp", "total_precip_in": "ToT Prcp", "hottest_day_temp": "Max Tmax", "cdd": "cdd"}


def assert_cutoff(df, name="table"):
    """Stop if any year is after 2018."""
    if "Year" in df.columns and df["Year"].max() > CUTOFF_YEAR:
        raise ValueError(f"{name}: found Year > {CUTOFF_YEAR} (max {df['Year'].max()})")


def dataset_revision():
    return HfApi().dataset_info(REPO).sha


def load_train():
    """annual_indices and coverage_and_stations. Returns (train_df, cov). Max Tmax is -inf in
    years where every day is missing, so +-inf becomes NaN. train_df is sorted by (ID, Year)."""
    train_df = pd.read_parquet(hf_hub_download(REPO, "annual_indices/train-00000-of-00001.parquet", repo_type="dataset"))
    cov = pd.read_parquet(hf_hub_download(REPO, "coverage_and_stations/train-00000-of-00001.parquet", repo_type="dataset"))
    assert_cutoff(train_df, "annual_indices")
    assert_cutoff(cov, "coverage_and_stations")
    train_df = train_df.replace([np.inf, -np.inf], np.nan)
    train_df = train_df.sort_values(["ID", "Year"]).reset_index(drop=True)
    return train_df, cov


def valid_flags(a, cov):
    """Per metric: True where the city-year has <=10 missing days of what the metric needs
    and the value is present."""
    days = a.Year.map(lambda y: 366 if calendar.isleap(y) else 365)
    # .to_numpy(): merge returns a fresh 0..n-1 index, so subtracting it from `days` (which keeps a's index)
    # would pair the wrong rows whenever `a` is a filtered slice (the held-back origins). Fixed 2026-11-08;
    # at origin 2018 the index is contiguous, so the submitted forecasts are unchanged.
    miss_both = days - a.merge(cov[["ID", "Year", "Days Both"]], on=["ID", "Year"], how="left")["Days Both"].to_numpy()
    v = {"annual_avg_temp": a[["Miss Tmax", "Miss Tmin"]].max(axis=1) <= 10, "total_precip_in": a["Miss Prcp"] <= 10,
         "hottest_day_temp": a["Miss Tmax"] <= 10, "cdd": miss_both <= 10}
    return {m: v[m] & a[c].notna() for m, c in METRICS.items()}
