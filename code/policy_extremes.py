"""Policy check 2: are cities seeing heat and cold they were not built for?

Thesis tested: "U.S. cities increasingly see temperatures outside what they were designed for: northern
cities get runs of consecutive extreme-heat days, and southern cities (e.g., Texas, February 2021) get
cold snaps they are not winterized for."

Each city's "design range" is its own 1976-2005 record (challenge `daily` table, up to 2018), a stand-in
for engineering design values such as ASHRAE's 99.6% / 0.4% design temperatures. Observed 2019-2025
(NOAA GHCN-Daily, obs_2018_2021.csv + obs_2021_2025.csv) is compared with it. ANALYSIS ONLY: never a
forecast input. Definitions were fixed before any result was computed (written to config first):

  heat day        daily high >= the city's 99th percentile of 1976-2005 daily highs (about 3.65 days/yr)
  cold day        daily low  <= the city's 1st percentile of 1976-2005 daily lows   (about 3.65 days/yr)
  heat-wave day   a heat day inside a run of >= 3 consecutive heat days (cold-snap day: same for cold)
  beyond record   any 2019-2025 day hotter than the 1976-2005 hottest day (colder than the coldest)
A year counts only if it misses <= 10 days of that variable. A city needs >= 15 valid baseline years
and >= 4 valid recent years. North = station latitude >= 40 N.

No-change benchmarks: rates stay at ~3.65 days/yr; and if nothing changed, the chance that the hottest
of 7 recent years beats the hottest of 30 baseline years is 7/37 = 19% (same for cold).

Run from the repo root:   python code/policy_extremes.py
Writes outputs/policy_extremes/: config.json, city_extremes.csv, summary.md
"""
import calendar
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from huggingface_hub import hf_hub_download

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shared import REPO, load_train

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs" / "policy_extremes"
CFG = {"baseline": [1976, 2005], "recent": [2019, 2025], "heat_pct": 99, "cold_pct": 1, "run_days": 3,
       "max_missing": 10, "min_base_years": 15, "min_recent_years": 4, "north_lat": 40.0,
       "null_record_prob": 7 / 37}


def load():
    d = pd.read_parquet(hf_hub_download(REPO, "daily/train-00000-of-00001.parquet", repo_type="dataset"))
    d["Date"] = pd.to_datetime(d["Date"].astype(str))
    base = d[d.Date.dt.year.between(*CFG["baseline"])][["ID", "Date", "tmax", "tmin"]]
    o = pd.concat([pd.read_csv(ROOT / f, dtype={"DATE": str}) for f in ("obs_2018_2021.csv", "obs_2021_2025.csv")])
    o = o.drop_duplicates(["ID", "DATE"])
    o["Date"] = pd.to_datetime(o.DATE)
    rec = pd.DataFrame({"ID": o.ID, "Date": o.Date, "tmax": o.TMAX / 10 * 9 / 5 + 32, "tmin": o.TMIN / 10 * 9 / 5 + 32})
    rec = rec[rec.Date.dt.year.between(*CFG["recent"])]
    return base, rec


def valid_years(df, col):
    g = df.assign(y=df.Date.dt.year).groupby(["ID", "y"])[col].count().reset_index()
    g["days"] = g.y.map(lambda y: 366 if calendar.isleap(y) else 365)
    return g[g.days - g[col] <= CFG["max_missing"]][["ID", "y"]]


def runs(flag, dates):
    """Days that sit in runs of >= run_days consecutive calendar days with flag True; and the longest run."""
    s = pd.Series(flag.values, index=dates.values).sort_index()
    s = s.reindex(pd.date_range(s.index.min(), s.index.max()), fill_value=False)
    grp = (s != s.shift()).cumsum()
    length = s.groupby(grp).transform("size").where(s, 0)
    return int((length >= CFG["run_days"]).sum()), int(length.max())


def per_city(df, col, thr, below, years):
    d = df.assign(y=df.Date.dt.year).merge(years, on=["ID", "y"])
    rows = {}
    for c, g in d.groupby("ID"):
        if c not in thr.index:
            continue
        flag = (g[col] <= thr[c]) if below else (g[col] >= thr[c])
        n_years = g.y.nunique()
        wave, longest = runs(flag, g.Date)
        rows[c] = {"years": n_years, "days_per_yr": flag.sum() / n_years, "wave_days_per_yr": wave / n_years,
                   "longest_run": longest, "extreme": g[col].min() if below else g[col].max()}
    return pd.DataFrame(rows).T


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "config.json").write_text(json.dumps(CFG, indent=2))       # before any result
    base, rec = load()
    train, _ = load_train()
    lat = train.groupby("ID")[["Name", "Lat", "Lon"]].first()
    out = []
    for kind, col, pct, below in (("heat", "tmax", CFG["heat_pct"], False), ("cold", "tmin", CFG["cold_pct"], True)):
        by, ry = valid_years(base, col), valid_years(rec, col)
        by = by[by.ID.map(by.ID.value_counts()) >= CFG["min_base_years"]]
        ry = ry[ry.ID.map(ry.ID.value_counts()) >= CFG["min_recent_years"]]
        b = base.assign(y=base.Date.dt.year).merge(by, on=["ID", "y"])
        thr = b.groupby("ID")[col].quantile(pct / 100)
        B, R = per_city(base, col, thr, below, by), per_city(rec, col, thr, below, ry)
        m = B.join(R, lsuffix="_base", rsuffix="_recent", how="inner")
        m["threshold_F"] = thr.reindex(m.index)
        m["beyond_record"] = (m.extreme_recent < m.extreme_base) if below else (m.extreme_recent > m.extreme_base)
        m.columns = [f"{kind}_{c}" for c in m.columns]
        out.append(m)
    df = lat.join(out[0], how="inner").join(out[1], how="inner")
    df["north"] = df.Lat >= CFG["north_lat"]
    df.index.name = "city_id"
    df.to_csv(OUT / "city_extremes.csv", float_format="%.3f")

    lines = ["# Are cities seeing heat and cold they were not built for?", "",
             "Design range = each city's own 1976-2005 record. Recent = observed NOAA 2019-2025 (analysis only). "
             "Definitions fixed in `config.json` before the results.", "",
             f"Cities with enough data: {len(df)} ({int(df.north.sum())} north of 40 N, {int((~df.north).sum())} south).", "",
             "| | Group | Days/yr past the 1% level: 1976-2005 -> 2019-2025 (median city) | Days/yr in runs of 3+ (median) | Cities where runs of 3+ rose | Cities beyond their 1976-2005 record (no-change: 19%) |",
             "|---|---|---|---|---|---|"]
    for kind in ("heat", "cold"):
        for name, sel in (("all", df.index == df.index), ("north", df.north), ("south", ~df.north)):
            x = df[sel]
            lines.append(f"| {kind} | {name} | {x[f'{kind}_days_per_yr_base'].median():.1f} -> {x[f'{kind}_days_per_yr_recent'].median():.1f} "
                         f"| {x[f'{kind}_wave_days_per_yr_base'].median():.1f} -> {x[f'{kind}_wave_days_per_yr_recent'].median():.1f} "
                         f"| {(x[f'{kind}_wave_days_per_yr_recent'] > x[f'{kind}_wave_days_per_yr_base']).mean():.0%} "
                         f"| {x[f'{kind}_beyond_record'].mean():.0%} ({int(x[f'{kind}_beyond_record'].sum())}) |")
    for kind, asc in (("heat", False), ("cold", False)):
        top = df.assign(r=df[f"{kind}_wave_days_per_yr_recent"] - df[f"{kind}_wave_days_per_yr_base"]).sort_values("r", ascending=asc).head(15)
        lines += ["", f"## Largest rise in {kind}-run days per year", "",
                  f"| City | Lat | Threshold F | Run days/yr 1976-2005 | 2019-2025 | Longest run 1976-2005 | 2019-2025 | Record then | 2019-2025 extreme |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for c, r in top.iterrows():
            lines.append(f"| {r.Name} | {r.Lat:.1f} | {r[f'{kind}_threshold_F']:.0f} | {r[f'{kind}_wave_days_per_yr_base']:.1f} | "
                         f"{r[f'{kind}_wave_days_per_yr_recent']:.1f} | {r[f'{kind}_longest_run_base']:.0f} | {r[f'{kind}_longest_run_recent']:.0f} | "
                         f"{r[f'{kind}_extreme_base']:.0f} | {r[f'{kind}_extreme_recent']:.0f} |")
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
