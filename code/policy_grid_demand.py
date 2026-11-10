"""Policy essay, section 3 (national): the grid as it has been, and how much heat moves demand, by U.S. region.

Data (all dated 2018-12-31 or earlier; data rule in code/AGENTS.md)
  - EIA-930 hourly demand of every balancing authority, July 2015 - December 2018 (the form starts July 2015),
    EIA "six-month files", cached in data/raw/grid/. Demand responds to the weather, so no file after 2018 is read.
    EIA groups the balancing authorities into 13 regions (column "Region").
  - Daily highs and lows: challenge `daily` table (up to 2018). Each challenge city is assigned to an EIA region
    by state (REGION_STATES below; El Paso and Amarillo by their grid). A region's temperature is the mean of its
    cities weighted by the city's county households (Census LACE 2023, outputs/cooling_gap/city_cooling_gap.csv).

Model (fixed before running; written to config.json first), summer days June-September, per region:
  daily peak  = year effect + weekday effect + b_day   * daily high      (afternoon peak)
  daily low   = year effect + weekday effect + b_night * daily low       (overnight floor)
  Sensitivities are also given as % of the region's 2018 mean summer daily peak (or low), so they compare
  across regions of different sizes. The year effect absorbs growth; b measures weather alone.
Also: the month of each region's yearly peak in 2016-2018 (summer- or winter-peaking: the cold side of the risk).

Run from the repo root:   python code/policy_grid_demand.py
Writes outputs/grid_national/: config.json, sensitivity.csv, peaks.csv, region_daily.csv, summary.md
"""
import json
import sys
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from huggingface_hub import hf_hub_download

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shared import REPO
import policy_grid_ercot as ge

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "grid"
OUT = ROOT / "outputs" / "grid_national"
HALVES = ["2015_Jul_Dec", "2016_Jan_Jun", "2016_Jul_Dec", "2017_Jan_Jun", "2017_Jul_Dec", "2018_Jan_Jun", "2018_Jul_Dec"]
URL = "https://www.eia.gov/electricity/gridmonitor/sixMonthFiles/EIA930_BALANCE_{}.csv"
REGION_STATES = {
    "TEX": ["TX"], "CAL": ["CA"], "NW": ["WA", "OR", "ID", "MT", "UT", "NV", "CO", "WY"], "SW": ["AZ", "NM"],
    "CENT": ["KS", "OK", "NE", "SD", "ND"], "MIDW": ["MN", "IA", "WI", "MI", "IN", "MO", "AR", "LA", "KY"],
    "MIDA": ["PA", "NJ", "MD", "DE", "VA", "WV", "OH", "IL", "DC"], "CAR": ["NC", "SC"], "SE": ["GA", "AL", "MS"],
    "TEN": ["TN"], "NE": ["ME", "NH", "VT", "MA", "RI", "CT"], "NY": ["NY"], "FLA": ["FL"]}
CITY_REGION = {"USW00023044": "SW", "USW00023047": "CENT"}      # El Paso (El Paso Electric), Amarillo (SPP)
UTC_OFFSET = {"NE": 5, "NY": 5, "MIDA": 5, "CAR": 5, "FLA": 5, "SE": 6, "TEN": 6, "MIDW": 6, "CENT": 6, "TEX": 6,
              "SW": 7, "NW": 8, "CAL": 8}                       # standard time; a day = local calendar day
CFG = {"halves": HALVES, "summer_months": [6, 7, 8, 9], "region_states": REGION_STATES, "city_region": CITY_REGION,
       "utc_offset": UTC_OFFSET, "min_hours_per_day": 23, "weights": "county households (LACE 2023)"}


def load_930():
    frames = []
    for h in HALVES:
        p = RAW / f"EIA930_BALANCE_{h}.csv"
        if not p.exists():
            RAW.mkdir(parents=True, exist_ok=True)
            req = urllib.request.Request(URL.format(h), headers={"User-Agent": "Mozilla/5.0 (research script)"})
            p.write_bytes(urllib.request.urlopen(req, timeout=600).read())
        d = pd.read_csv(p, thousands=",", low_memory=False,
                        usecols=["Balancing Authority", "UTC Time at End of Hour", "Demand (MW)", "Demand (MW) (Adjusted)", "Region"])
        d["MW"] = d["Demand (MW) (Adjusted)"].fillna(d["Demand (MW)"])
        d["utc"] = pd.to_datetime(d["UTC Time at End of Hour"], format="%m/%d/%Y %I:%M:%S %p")
        frames.append(d[["Balancing Authority", "Region", "utc", "MW"]].dropna(subset=["MW"]))
    d = pd.concat(frames, ignore_index=True)
    d = d[(d.MW > 0) & d.Region.isin(UTC_OFFSET)]
    assert d.utc.max() <= pd.Timestamp("2019-01-01 08:00"), "EIA-930 data after 2018"
    return d.rename(columns={"Balancing Authority": "BA"})


def region_hourly(d):
    """Region demand per hour, only for hours in which every BA that usually reports in that month reported."""
    out = []
    for reg, g in d.groupby("Region"):
        g = g.assign(month=g.utc.dt.to_period("M"))
        usual = g.groupby(["month", "BA"]).size().reset_index(name="n")
        usual = usual[usual.n >= 0.9 * usual.groupby("month").n.transform("max")]
        g = g.merge(usual[["month", "BA"]], on=["month", "BA"])
        need = usual.groupby("month").BA.nunique()
        h = g.groupby(["month", "utc"]).agg(MW=("MW", "sum"), n=("BA", "nunique")).reset_index()
        h = h[h.n == h.month.map(need)]
        h["Region"] = reg
        h["local"] = h.utc - pd.Timedelta(hours=UTC_OFFSET[reg]) - pd.Timedelta(minutes=30)
        out.append(h[["Region", "utc", "local", "MW"]])
    return pd.concat(out, ignore_index=True)


def city_region_table():
    cg = pd.read_csv(ROOT / "outputs" / "cooling_gap" / "city_cooling_gap.csv", dtype={"county_fips": str})
    st2reg = {s: r for r, ss in REGION_STATES.items() for s in ss}
    cg["Region"] = cg.city_id.map(CITY_REGION).fillna(cg.state.map(st2reg))
    return cg.dropna(subset=["Region"])[["city_id", "Name", "state", "Region", "households", "no_ac_pct"]]


def region_weather(cities, years):
    w = pd.read_parquet(hf_hub_download(REPO, "daily/train-00000-of-00001.parquet", repo_type="dataset"),
                        columns=["ID", "Date", "tmax", "tmin"])
    w["Date"] = pd.to_datetime(w["Date"].astype(str))
    assert w.Date.max() <= pd.Timestamp("2018-12-31"), "daily weather after 2018"
    w = w[w.Date.dt.year.between(*years)].merge(cities[["city_id", "Region", "households"]], left_on="ID", right_on="city_id")
    out = []
    for col in ("tmax", "tmin"):
        x = w.dropna(subset=[col])
        t = x.assign(v=x[col] * x.households).groupby(["Region", "Date"]).agg(v=("v", "sum"), wt=("households", "sum"))
        out.append((t.v / t.wt).rename(col))
    return pd.concat(out, axis=1).reset_index()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "config.json").write_text(json.dumps(CFG, indent=2))            # before any result
    hourly = region_hourly(load_930())
    hourly["DATE"] = hourly.local.dt.normalize()
    day = hourly.groupby(["Region", "DATE"]).agg(peak=("MW", "max"), low=("MW", "min"), n=("MW", "size")).reset_index()
    day = day[day.n >= CFG["min_hours_per_day"]]

    cities = city_region_table()
    T = region_weather(cities, (2015, 2018)).rename(columns={"Date": "DATE"})
    day = day.merge(T, on=["Region", "DATE"], how="inner")
    day["Year"] = day.DATE.dt.year
    day.to_csv(OUT / "region_daily.csv", index=False, float_format="%.2f")

    rows = []
    for reg, g in day.groupby("Region"):
        s = g[g.DATE.dt.month.isin(CFG["summer_months"])].reset_index(drop=True)
        if len(s) < 200 or s.Year.nunique() < 3:
            continue
        bd, sd, r2d = ge.fit(ge.design(s, "tmax", None), s.peak.to_numpy(float))
        bn, sn, r2n = ge.fit(ge.design(s, "tmin", None), s.low.to_numpy(float))
        m18 = s[s.Year == 2018]
        rows.append({"Region": reg, "summer_days": len(s), "cities": int((cities.Region == reg).sum()),
                     "MW_per_F_day": bd[-1], "se_day": sd[-1], "r2_day": r2d, "pct_per_F_day": bd[-1] / m18.peak.mean() * 100,
                     "MW_per_F_night": bn[-1], "se_night": sn[-1], "r2_night": r2n, "pct_per_F_night": bn[-1] / m18.low.mean() * 100,
                     "mean_summer_peak_2018_MW": m18.peak.mean(), "mean_summer_low_2018_MW": m18.low.mean(),
                     "summer_tmax_2018_F": m18.tmax.mean()})
    sens = pd.DataFrame(rows).set_index("Region").sort_values("pct_per_F_day", ascending=False)

    pk = []
    for (reg, y), g in hourly.assign(Year=hourly.local.dt.year).groupby(["Region", "Year"]):
        if y < 2016 or g.local.dt.month.nunique() < 12:
            continue
        i = g.MW.idxmax()
        pk.append({"Region": reg, "Year": y, "peak_MW": g.MW.max(), "peak_month": g.loc[i, "local"].month})
    peaks = pd.DataFrame(pk)
    peaks["season"] = np.where(peaks.peak_month.isin([6, 7, 8, 9]), "summer", np.where(peaks.peak_month.isin([12, 1, 2]), "winter", "other"))
    peaks.to_csv(OUT / "peaks.csv", index=False)
    winter = peaks.groupby("Region").season.agg(lambda s: (s == "winter").sum())
    sens["winter_peak_years_2016_2018"] = winter.reindex(sens.index).fillna(0).astype(int)
    sens["peak_2018_MW"] = peaks[peaks.Year == 2018].set_index("Region").peak_MW.reindex(sens.index)
    sens.to_csv(OUT / "sensitivity.csv", float_format="%.3f")

    # national: all regions together, hours where every region is present
    nat_h = hourly.pivot_table(index="utc", columns="Region", values="MW").dropna()
    nat = nat_h.sum(axis=1).rename("MW").reset_index()
    nat["DATE"] = (nat.utc - pd.Timedelta(hours=6)).dt.normalize()
    nd = nat.groupby("DATE").agg(peak=("MW", "max"), n=("MW", "size")).reset_index()
    nd = nd[nd.n >= CFG["min_hours_per_day"]]
    allT = region_weather(cities.assign(Region="US"), (2015, 2018)).rename(columns={"Date": "DATE"})
    nd = nd.merge(allT, on="DATE")
    nd["Year"] = nd.DATE.dt.year
    ns = nd[nd.DATE.dt.month.isin(CFG["summer_months"])].reset_index(drop=True)
    bN, sN, r2N = ge.fit(ge.design(ns, "tmax", None), ns.peak.to_numpy(float))
    nat_pct = bN[-1] / ns[ns.Year == 2018].peak.mean() * 100

    L = ["# Section 3 (national): how heat moves electricity demand, by U.S. region", "",
         "Hourly demand: EIA-930, July 2015 - December 2018 (13 EIA regions). Temperatures: challenge daily data, "
         "challenge cities in each region weighted by county households. Summer = June-September. All data up to 2018.", "",
         f"**Contiguous U.S. (all 13 regions, {len(ns):,} summer days): +{bN[-1]:,.0f} MW of daily peak per 1 F of the "
         f"household-weighted daily high (se {sN[-1]:,.0f}), {nat_pct:.1f}% per F; R squared {r2N:.2f}.**", "",
         "| Region | Cities | Summer days | Peak: MW per F | Peak: % per F | Night floor: MW per F | Night: % per F | Fit (day / night) | 2018 summer mean peak (MW) | Winter-peaking years 2016-18 |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for reg, r in sens.iterrows():
        L.append(f"| {reg} | {int(r.cities)} | {int(r.summer_days)} | {r.MW_per_F_day:,.0f} | {r.pct_per_F_day:.1f}% | {r.MW_per_F_night:,.0f} | "
                 f"{r.pct_per_F_night:.1f}% | {r.r2_day:.2f} / {r.r2_night:.2f} | {r.mean_summer_peak_2018_MW:,.0f} | {int(r.winter_peak_years_2016_2018)} of 3 |")
    L += ["", f"- Median region: {sens.pct_per_F_day.median():.1f}% more peak demand per F of daily high; "
          f"{sens.pct_per_F_night.median():.1f}% higher overnight floor per F of daily low.",
          f"- Regions whose yearly peak came in winter at least once in 2016-2018: "
          f"{', '.join(sens.index[sens.winter_peak_years_2016_2018 > 0]) or 'none'}.",
          "", "## Limits", "",
          "- Only 3.5 summers (EIA-930 starts July 2015); ERCOT's own 2002-2018 record (code/policy_grid_ercot.py) is the long-run check.",
          "- Regions are EIA's groupings of balancing authorities; cities are assigned by state, which is approximate at borders.",
          "- Load is what customers drew; on emergency days demand was cut, so heat's effect is understated.",
          "- Airport temperatures; regions with few challenge cities have noisier temperatures."]
    (OUT / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
