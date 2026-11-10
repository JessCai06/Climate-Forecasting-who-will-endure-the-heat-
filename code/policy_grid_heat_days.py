"""Policy essay, section 2: the forecast weather, counted against the livability line (essay section 1b).

Livability lines (docs/policy_essay_outline.md, section 1b; fixed in config.json before any result):
  cooling-required day   daily high >= 95 F (35 C): fans stop protecting, homes without cooling pass 82 F indoors
  hot night              daily low  >= 75 F (24 C): the WHO healthy indoor maximum; homes cannot cool down overnight
Also reported, because they drive grid demand (essay sections 3 and 5): cooling degree days (cdd) and the
hottest day of the year.

Periods
  baseline   1976-2005, challenge `daily` / `annual_indices` (the climate the grid was built for)
  forecast   2019-2025, made with data up to 2018 only:
               - days and nights: same delta method as code/policy_cooling_gap.py (and the submitted cdd
                 forecast, Experiment 5B). Take the city's real daily highs/lows from its last 10 valid
                 years up to 2018, warm them by the shared slope of Avg Tmax / Avg Tmin (30 years to 2018)
                 x (year - those years' middle year), and count days past the line.
               - cdd and hottest day: the submitted forecast, submission.csv (mean of 2019-2025).
  observed   2019-2025, NOAA GHCN-Daily (obs_*.csv, already in the repo for the approved policy analysis).
             ANALYSIS ONLY: shown as a check, never used to make or choose the forecast.
A year counts only if it misses <= 10 days of the variable. A city needs >= 15 valid baseline years
(and >= 4 valid observed years for the check).

Run from the repo root:   python code/policy_grid_heat_days.py
Writes outputs/grid_heat_days/: config.json, city_heat_days.csv, summary.md
"""
import calendar
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shared import load_train, valid_flags
import exp02_line_forest as e2
import exp05_levels_slopes as e5
import exp05b_daily_distribution as e5b

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs" / "grid_heat_days"
CFG = {"hot_day_F": 95.0, "hot_night_F": 75.0, "baseline": [1976, 2005], "forecast": [2019, 2025],
       "recent_years_for_days": 10, "max_missing": 10, "min_base_years": 15, "min_obs_years": 4}


def days_in(y):
    return 366 if calendar.isleap(y) else 365


def valid_years(daily, col):
    n = daily.dropna(subset=[col]).groupby(["ID", "Year"]).size().rename("n").reset_index()
    n = n[n.Year.map(days_in) - n.n <= CFG["max_missing"]]
    return n[["ID", "Year"]]


def per_year_counts(daily, col, thr):
    """Days per valid year at or above thr, scaled to a full year for the few missing days."""
    ok = valid_years(daily, col)
    d = daily.merge(ok, on=["ID", "Year"]).dropna(subset=[col])
    g = d.assign(hit=d[col] >= thr).groupby(["ID", "Year"]).agg(hit=("hit", "sum"), n=("hit", "size")).reset_index()
    g["per_yr"] = g.hit * g.Year.map(days_in) / g.n
    return g


def forecast_counts(daily, col, thr, slope):
    """Delta method: last 10 valid years up to 2018, warmed by slope, mean count over 2019-2025."""
    g = per_year_counts(daily, col, thr)[["ID", "Year"]]
    d = daily.merge(g, on=["ID", "Year"]).dropna(subset=[col])
    yrs = np.arange(CFG["forecast"][0], CFG["forecast"][1] + 1)
    out = {}
    for c, x in d.groupby("ID"):
        last = sorted(x.Year.unique())[-CFG["recent_years_for_days"]:]
        if len(last) < CFG["recent_years_for_days"]:
            continue
        piv = np.mean(last)
        per = [(x.loc[x.Year == y, col].to_numpy(), days_in(y) / (x.Year == y).sum()) for y in last]
        out[c] = float(np.mean([np.mean([(t + slope * (Y - piv) >= thr).sum() * s for t, s in per]) for Y in yrs]))
    return pd.Series(out)


def load_observed():
    o = pd.concat([pd.read_csv(ROOT / f, dtype={"DATE": str}) for f in ("obs_2018_2021.csv", "obs_2021_2025.csv")])
    o = o.drop_duplicates(["ID", "DATE"])
    o["Year"] = pd.to_datetime(o.DATE).dt.year
    o = o[o.Year.between(*CFG["forecast"])]
    return pd.DataFrame({"ID": o.ID, "Year": o.Year, "tmax": o.TMAX / 10 * 9 / 5 + 32, "tmin": o.TMIN / 10 * 9 / 5 + 32})


def mean_over(g, years, min_years):
    x = g[g.Year.between(*years)]
    n = x.groupby("ID").size()
    return x.groupby("ID").per_yr.mean()[n >= min_years]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "config.json").write_text(json.dumps(CFG, indent=2))            # before any result

    train, cov = load_train()
    d18 = train[train.Year <= 2018]
    slopes = {}
    for col, avg, miss in (("tmax", "Avg Tmax", "Miss Tmax"), ("tmin", "Avg Tmin", "Miss Tmin")):
        ser = e2._window_series(d18, d18[avg].where(d18[miss] <= CFG["max_missing"]), 2018)
        slopes[col] = e5._shared_slope(ser, sorted(c for c, s in ser.items() if len(s) >= e2.MIN_VALID))

    daily = e5b.load_daily()                                                  # asserts nothing after 2018
    obs = load_observed()
    names = train.groupby("ID")[["Name", "Lat", "Lon"]].first()
    df = names.copy()
    for key, col, thr in (("hot_days", "tmax", CFG["hot_day_F"]), ("hot_nights", "tmin", CFG["hot_night_F"])):
        base = per_year_counts(daily, col, thr)
        df[f"{key}_base"] = mean_over(base, CFG["baseline"], CFG["min_base_years"])
        df[f"{key}_fc"] = forecast_counts(daily[daily.Year <= 2018], col, thr, slopes[col])
        df[f"{key}_obs"] = mean_over(per_year_counts(obs, col, thr), CFG["forecast"], CFG["min_obs_years"])

    flags = valid_flags(train, cov)
    a = train.assign(cdd_v=train.cdd.where(flags["cdd"]), hot_v=train["Max Tmax"].where(flags["hottest_day_temp"]))
    ab = a[a.Year.between(*CFG["baseline"])].groupby("ID")
    df["cdd_base"] = ab.cdd_v.mean().where(ab.cdd_v.count() >= CFG["min_base_years"])
    df["hottest_base"] = ab.hot_v.mean().where(ab.hot_v.count() >= CFG["min_base_years"])
    sub = pd.read_csv(ROOT / "submission.csv").pivot_table(index="city_id", columns="metric", values="predicted_value")
    df["cdd_fc"] = sub["cdd"]
    df["hottest_fc"] = sub["hottest_day_temp"]

    sc = pd.read_csv(ROOT / "outputs" / "policy_check" / "station_county.csv", dtype=str).set_index("ID")
    df = df.join(sc[["county_name", "state"]])
    df = df.dropna(subset=["hot_days_base", "hot_days_fc", "hot_nights_base", "hot_nights_fc", "cdd_base", "cdd_fc"])
    df["cdd_change_pct"] = (df.cdd_fc / df.cdd_base - 1) * 100
    df.index.name = "city_id"
    df.to_csv(OUT / "city_heat_days.csv", float_format="%.3f")

    # ------------------------------------------------------------------ summary
    n = len(df)
    chk = df.dropna(subset=["hot_days_obs"])
    r_days = chk[["hot_days_fc", "hot_days_obs"]].corr(method="spearman").iloc[0, 1]
    chk_n = df.dropna(subset=["hot_nights_obs"])
    r_nights = chk_n[["hot_nights_fc", "hot_nights_obs"]].corr(method="spearman").iloc[0, 1]
    L = ["# Section 2: the forecast weather against the livability line", "",
         f"Cities: {n}. Cooling-required day = high >= {CFG['hot_day_F']:.0f} F; hot night = low >= {CFG['hot_night_F']:.0f} F. "
         f"Baseline {CFG['baseline'][0]}-{CFG['baseline'][1]}; forecast {CFG['forecast'][0]}-{CFG['forecast'][1]} from data up to 2018 "
         f"(shared slopes: Tmax {slopes['tmax']:.4f} F/yr, Tmin {slopes['tmin']:.4f} F/yr; cdd and hottest day from submission.csv). "
         "Observed 2019-2025 is NOAA data used as a check only.", "",
         "## All cities", "",
         "| Measure | Baseline (median city) | Forecast (median city) | Observed (median city) | Total across cities: baseline -> forecast |",
         "|---|---|---|---|---|"]
    for key, label in (("hot_days", "Cooling-required days per year"), ("hot_nights", "Hot nights per year")):
        L.append(f"| {label} | {df[f'{key}_base'].median():.1f} | {df[f'{key}_fc'].median():.1f} | {df[f'{key}_obs'].median():.1f} | "
                 f"{df[f'{key}_base'].sum():,.0f} -> {df[f'{key}_fc'].sum():,.0f} |")
    L.append(f"| Cooling degree days | {df.cdd_base.median():,.0f} | {df.cdd_fc.median():,.0f} | - | median change {df.cdd_change_pct.median():+.0f}% |")
    L.append(f"| Hottest day of the year (F) | {df.hottest_base.median():.1f} | {df.hottest_fc.median():.1f} | - | |")
    L += ["",
          f"- Cities with at least one cooling-required day a year: baseline {(df.hot_days_base >= 1).sum()}, forecast {(df.hot_days_fc >= 1).sum()}.",
          f"- Cities with at least 30 (a month of them): baseline {(df.hot_days_base >= 30).sum()}, forecast {(df.hot_days_fc >= 30).sum()}.",
          f"- Cities with at least one hot night a year: baseline {(df.hot_nights_base >= 1).sum()}, forecast {(df.hot_nights_fc >= 1).sum()}.",
          f"- Cities where cooling-required days rise: {(df.hot_days_fc > df.hot_days_base).sum()}; hot nights rise: {(df.hot_nights_fc > df.hot_nights_base).sum()}; cdd rise: {(df.cdd_fc > df.cdd_base).sum()}.",
          f"- Check (analysis only): rank correlation of forecast vs observed across cities: cooling-required days {r_days:.2f} ({len(chk)} cities), hot nights {r_nights:.2f} ({len(chk_n)} cities).",
          "", "## By state (sum over the challenge cities in each state, days per year)", "",
          "| State | Cities | Cooling-required days: baseline -> forecast | Hot nights: baseline -> forecast | cdd change (median) |", "|---|---|---|---|---|"]
    st = df.groupby("state").agg(cities=("Name", "size"), hd_b=("hot_days_base", "sum"), hd_f=("hot_days_fc", "sum"),
                                 hn_b=("hot_nights_base", "sum"), hn_f=("hot_nights_fc", "sum"), cdd=("cdd_change_pct", "median"))
    for s, r in st.assign(rise=st.hd_f - st.hd_b).sort_values("rise", ascending=False).iterrows():
        L.append(f"| {s} | {r.cities} | {r.hd_b:.0f} -> {r.hd_f:.0f} | {r.hn_b:.0f} -> {r.hn_f:.0f} | {r.cdd:+.0f}% |")
    for key, label in (("hot_days", "cooling-required days"), ("hot_nights", "hot nights")):
        top = df.assign(r=df[f"{key}_fc"] - df[f"{key}_base"]).sort_values("r", ascending=False).head(15)
        L += ["", f"## Largest rise in {label} per year", "",
              "| City | State | Baseline | Forecast | Observed (check) | cdd baseline -> forecast |", "|---|---|---|---|---|---|"]
        for c, r in top.iterrows():
            obs_v = "-" if pd.isna(r[f"{key}_obs"]) else f"{r[f'{key}_obs']:.1f}"
            L.append(f"| {r.Name} | {r.state} | {r[f'{key}_base']:.1f} | {r[f'{key}_fc']:.1f} | {obs_v} | {r.cdd_base:,.0f} -> {r.cdd_fc:,.0f} |")
    L += ["", "## Limits", "",
          "- Stations are mostly at airports, outside dense city centres, so heat where people live is probably understated (urban heat island).",
          "- Dry-bulb lines only: the data has no humidity, so humid cities' risk is understated (essay section 1b).",
          "- The delta method shifts the whole distribution by the shared slope; it does not change the shape of heat waves."]
    (OUT / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
