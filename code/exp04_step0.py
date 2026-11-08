"""Exp04 STEP 0 (report only): how many city-metrics have gaps? Writes outputs/exp04/step0_counts.csv"""
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from shared import METRICS, load_train, valid_flags

ROOT = Path(__file__).resolve().parent.parent


def step0(a, cov):
    flags = valid_flags(a, cov)
    cities = sorted(a.ID.unique())
    w = a.Year.between(1989, 2018)
    rows = []
    for m in METRICS:
        ok = flags[m]
        n_win = (ok & w).groupby(a.ID).sum().reindex(cities).fillna(0)
        last = a[ok].groupby("ID").Year.max().reindex(cities)
        rows.append({"metric": m, "n_city_metrics": len(cities),
                     "a_gaps_in_1989_2018": int((n_win < 30).sum()),
                     "b_last_valid_before_2018": int((last.isna() | (last < 2018)).sum()),
                     "c_fewer_than_10_valid": int((n_win < 10).sum())})
    df = pd.DataFrame(rows)
    tot = df.drop(columns="metric").sum()
    tot["metric"] = "ALL"
    df = pd.concat([df, tot.to_frame().T], ignore_index=True)
    for k in ("a", "b", "c"):
        col = [c for c in df.columns if c.startswith(k + "_")][0]
        df[col + "_pct"] = (df[col].astype(float) / df.n_city_metrics.astype(float) * 100).round(1)
    return df


if __name__ == "__main__":
    a, cov = load_train()
    df = step0(a, cov)
    (ROOT / "outputs" / "exp04").mkdir(parents=True, exist_ok=True)
    df.to_csv(ROOT / "outputs" / "exp04" / "step0_counts.csv", index=False)
    print(df.to_string(index=False))
