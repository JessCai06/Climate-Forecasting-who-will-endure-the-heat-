import pandas as pd
import numpy as np
from datasets import load_dataset
from sklearn.ensemble import RandomForestRegressor

# 1. Load the yearly data (up to 2018)
ds = load_dataset("CMU-OSPO/protostar-climate-train-to-2018", "annual_indices")
train_df = ds["train"].to_pandas()

# Metric codes and their columns in annual_indices:
# annual_avg_temp = "Avg Temp", total_precip_in = "ToT Prcp",
# hottest_day_temp = "Max Tmax", cdd = "cdd"
target = "Avg Temp"

# 2. Build lag features: each city's value 1, 2 and 3 rows (years) earlier
train_df = train_df.sort_values(["ID", "Year"])
for k in (1, 2, 3):
    train_df[f"lag_{k}"] = train_df.groupby("ID")[target].shift(k)
features = ["lag_1", "lag_2", "lag_3"]
fit_df = train_df.dropna(subset=features + [target])

model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(fit_df[features], fit_df[target])

# 3. Predict 2019-2025 iteratively
# ... generate predictions and save to submission.csv

# 4. Check your error locally against validation years:
def compute_mae(actual, predicted):
    return np.mean(np.abs(actual - predicted))