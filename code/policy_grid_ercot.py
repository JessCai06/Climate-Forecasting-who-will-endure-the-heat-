"""Policy essay, section 3: the grid as it has been. Lead case: ERCOT (the Texas grid), 2002-2018.

Questions
  1. How have ERCOT's yearly energy and peak demand grown?
  2. How much does demand rise with heat? (the weather link that section 5 applies to the forecast)
     - daily PEAK load vs the day's high temperature (summer, June-September)
     - daily MINIMUM load (the night) vs the day's low temperature: what hot nights do to the grid
     - daily ENERGY vs cooling degree days

Data (all dated 2018-12-31 or earlier; data rule in code/AGENTS.md):
  - ERCOT hourly load by weather zone, 2002-2018 (ercot.com/gridinfo/load/load_hist), cached in data/raw/grid/.
    Energy demand responds to the weather, so no file after 2018 is downloaded here.
  - Daily highs and lows: challenge `daily` table (up to 2018), one airport station per ERCOT weather zone:
      COAST = Houston, NCENT = Dallas-Fort Worth, SCENT = mean of Austin and San Antonio,
      SOUTH = Corpus Christi, WEST = Abilene.
    The Texas temperature is the mean of those zones, weighted by each zone's share of 2002-2018 load.
    EAST, FWEST and NORTH (about 12% of load) have no challenge station and are left out of the weights.

Model (fixed before running; written to config.json first)
  summer day (Jun-Sep):  load = year effect + weekday effect + b1 * T + b2 * max(T - 95, 0)
  b1 is MW per F below 95 F; b1 + b2 is MW per F on cooling-required days (section 1b's 95 F line).
  The year effect absorbs growth (population, economy), so b1 and b2 measure the weather alone.
  Sensitivities are also given as % of the 2018 mean summer daily peak, so they can be carried to other grids.

Run from the repo root:   python code/policy_grid_ercot.py
Writes outputs/grid_ercot/: config.json, annual.csv, daily_summer.csv, fits.json, summary.md
"""
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd


sys.path.insert(0, str(Path(__file__).resolve().parent))
from shared import REPO, train_file

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "grid"
OUT = ROOT / "outputs" / "grid_ercot"
BASE = "https://www.ercot.com/files/docs/"
FILES = {**{y: f"2015/10/22/{y}_ercot_hourly_load_data.xls" for y in range(2002, 2015)},
         2015: "2016/01/07/native_load_2015.xls", 2016: "2017/01/10/native_Load_2016.zip",
         2017: "2018/01/09/native_load_2017.zip", 2018: "2019/01/07/native_load_2018.zip"}
ZONES = {"COAST": ["USW00012960"], "NCENT": ["USW00003927"], "SCENT": ["USW00013958", "USW00012921"],
         "SOUTH": ["USW00012924"], "WEST": ["USW00013962"]}
CFG = {"years": [2002, 2018], "summer_months": [6, 7, 8, 9], "hinge_F": 95.0, "cdd_base_F": 65.0,
       "zones": ZONES, "source": "ERCOT native load archives"}


def load_year(y):
    ext = FILES[y].rsplit(".", 1)[1]
    p = RAW / f"ercot_{y}.{ext}"
    if not p.exists():
        RAW.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(BASE + FILES[y], headers={"User-Agent": "Mozilla/5.0 (research script)"})
        p.write_bytes(urllib.request.urlopen(req, timeout=120).read())
    if ext == "zip":
        z = zipfile.ZipFile(p)
        df = pd.read_excel(z.open(z.namelist()[0]))
    else:
        df = pd.read_excel(p)
    df.columns = [str(c).strip().upper() for c in df.columns]
    df = df.rename(columns={"HOUR_END": "HOUR", "HOURENDING": "HOUR", "HOUR ENDING": "HOUR", "FAR_WEST": "FWEST", "NORTH_C": "NCENT",
                            "SOUTHERN": "SOUTH", "SOUTH_C": "SCENT"})
    h = df["HOUR"]
    if not np.issubdtype(h.dtype, np.datetime64):            # "01/01/2018 24:00" style, possibly with " DST"
        s = h.astype(str).str.replace(" DST", "", regex=False)
        day = pd.to_datetime(s.str.slice(0, 10), format="%m/%d/%Y")
        hr = s.str.slice(11, 13).astype(int)
        h = day + pd.to_timedelta(hr, unit="h")
    else:
        h = h.dt.round("h")
    df["TIME"] = h - pd.Timedelta(minutes=30)                   # hour ending -> middle of the hour
    df["DATE"] = df.TIME.dt.normalize()
    keep = ["DATE", "TIME", "ERCOT"] + [z for z in ["COAST", "EAST", "FWEST", "NORTH", "NCENT", "SOUTH", "SCENT", "WEST"] if z in df]
    return df[keep]


def fit(X, y):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ beta
    dof = len(y) - X.shape[1]
    cov = np.linalg.inv(X.T @ X) * (res @ res) / dof
    r2 = 1 - (res @ res) / ((y - y.mean()) @ (y - y.mean()))
    return beta, np.sqrt(np.diag(cov)), r2


def design(df, tcol, hinge):
    yrs = sorted(df.Year.unique())
    cols = [np.ones(len(df))] + [(df.Year == y).astype(float).to_numpy() for y in yrs[1:]]
    cols += [(df.DATE.dt.dayofweek == d).astype(float).to_numpy() for d in range(1, 7)]
    T = df[tcol].to_numpy(float)
    cols += [T]
    if hinge is not None:
        cols += [np.maximum(T - hinge, 0)]
    return np.column_stack(cols)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "config.json").write_text(json.dumps(CFG, indent=2))            # before any result

    load = pd.concat([load_year(y) for y in range(CFG["years"][0], CFG["years"][1] + 1)], ignore_index=True)
    load = load[load.DATE.dt.year.between(*CFG["years"])]
    assert load.DATE.max() <= pd.Timestamp("2018-12-31"), "load data after 2018"

    # ---- 1. annual growth
    ann = load.assign(Year=load.DATE.dt.year).groupby("Year").agg(
        energy_TWh=("ERCOT", lambda s: s.sum() / 1e6), peak_MW=("ERCOT", "max"),
        hours=("ERCOT", "size"))
    ann["peak_date"] = load.loc[load.groupby(load.DATE.dt.year).ERCOT.idxmax(), "DATE"].dt.strftime("%Y-%m-%d").to_numpy()
    summer = load[load.DATE.dt.month.isin(CFG["summer_months"])]
    ann["summer_energy_share"] = summer.groupby(summer.DATE.dt.year).ERCOT.sum() / load.groupby(load.DATE.dt.year).ERCOT.sum()
    ann["peak_month"] = pd.to_datetime(ann.peak_date).dt.month
    ann["hours_above_90pct_peak"] = load.assign(Year=load.DATE.dt.year).groupby("Year").apply(
        lambda g: int((g.ERCOT >= 0.9 * g.ERCOT.max()).sum()), include_groups=False)
    ann.to_csv(OUT / "annual.csv", float_format="%.3f")
    yrs = ann.index.to_numpy(float)
    g_energy = np.polyfit(yrs, np.log(ann.energy_TWh), 1)[0]
    g_peak = np.polyfit(yrs, np.log(ann.peak_MW), 1)[0]

    # ---- 2. weather link
    zone_share = load[list(ZONES)].sum() / load[list(ZONES)].sum().sum()
    w = pd.read_parquet(train_file("daily/train-00000-of-00001.parquet"),
                        columns=["ID", "Date", "tmax", "tmin"])
    w["Date"] = pd.to_datetime(w["Date"].astype(str))
    assert w.Date.max() <= pd.Timestamp("2018-12-31"), "daily weather after 2018"
    w = w[w.Date.dt.year.between(*CFG["years"])]
    zt = {}
    for z, ids in ZONES.items():
        x = w[w.ID.isin(ids)].groupby("Date")[["tmax", "tmin"]].mean()
        zt[z] = x
    T = pd.DataFrame({"tmax": sum(zt[z].tmax * zone_share[z] for z in ZONES),
                      "tmin": sum(zt[z].tmin * zone_share[z] for z in ZONES)}).dropna()

    day = load.groupby("DATE").agg(peak=("ERCOT", "max"), low=("ERCOT", "min"), energy=("ERCOT", "sum"), n=("ERCOT", "size"))
    day = day[day.n >= 23].join(T, how="inner").rename_axis("DATE").reset_index()
    day["Year"] = day.DATE.dt.year
    day["cdd"] = np.maximum((day.tmax + day.tmin) / 2 - CFG["cdd_base_F"], 0)
    s = day[day.DATE.dt.month.isin(CFG["summer_months"])].reset_index(drop=True)
    s.to_csv(OUT / "daily_summer.csv", index=False, float_format="%.2f")

    mean_peak_2018 = s[s.Year == 2018].peak.mean()
    mean_low_2018 = s[s.Year == 2018].low.mean()
    mean_energy_2018 = s[s.Year == 2018].energy.mean()
    b_pk, se_pk, r2_pk = fit(design(s, "tmax", CFG["hinge_F"]), s.peak.to_numpy(float))
    b_lo, se_lo, r2_lo = fit(design(s, "tmin", None), s.low.to_numpy(float))
    b_en, se_en, r2_en = fit(design(s, "cdd", None), s.energy.to_numpy(float))
    fits = {
        "peak_vs_tmax": {"MW_per_F_below_95": b_pk[-2], "se": se_pk[-2], "extra_MW_per_F_above_95": b_pk[-1], "se_extra": se_pk[-1],
                         "MW_per_F_above_95": b_pk[-2] + b_pk[-1], "r2": r2_pk, "pct_per_F_below_95": b_pk[-2] / mean_peak_2018 * 100,
                         "pct_per_F_above_95": (b_pk[-2] + b_pk[-1]) / mean_peak_2018 * 100, "mean_summer_peak_2018_MW": mean_peak_2018},
        "night_low_vs_tmin": {"MW_per_F": b_lo[-1], "se": se_lo[-1], "r2": r2_lo, "pct_per_F": b_lo[-1] / mean_low_2018 * 100,
                              "mean_summer_low_2018_MW": mean_low_2018},
        "energy_vs_cdd": {"MWh_per_cdd": b_en[-1], "se": se_en[-1], "r2": r2_en, "pct_per_cdd": b_en[-1] / mean_energy_2018 * 100,
                          "mean_summer_day_2018_MWh": mean_energy_2018},
        "zone_weights": zone_share.round(4).to_dict(), "summer_days": int(len(s)),
        "growth_per_yr": {"energy": g_energy, "peak": g_peak},
    }
    (OUT / "fits.json").write_text(json.dumps(fits, indent=2, default=float))

    # ---- summary
    f1, f2, f3 = fits["peak_vs_tmax"], fits["night_low_vs_tmin"], fits["energy_vs_cdd"]
    hot = s[s.tmax >= CFG["hinge_F"]]
    L = ["# Section 3: ERCOT, the grid as it has been (2002-2018)", "",
         "Hourly load: ERCOT native load archives. Temperature: challenge daily data at Houston, Dallas-Fort Worth, Austin, "
         f"San Antonio, Corpus Christi and Abilene, weighted by zone load (weights cover {len(ZONES)} of 8 zones). All data up to 2018.", "",
         "## 1. Growth", "",
         f"- Yearly energy: {ann.energy_TWh.iloc[0]:.0f} TWh in {int(yrs[0])} -> {ann.energy_TWh.iloc[-1]:.0f} TWh in {int(yrs[-1])} "
         f"(trend {g_energy*100:+.1f}% a year).",
         f"- Yearly peak: {ann.peak_MW.iloc[0]:,.0f} MW -> {ann.peak_MW.iloc[-1]:,.0f} MW (trend {g_peak*100:+.1f}% a year). "
         f"The peak fell in summer (June-September) in {int(ann.peak_month.isin(CFG['summer_months']).sum())} of {len(ann)} years.",
         f"- Summer (June-September) share of yearly energy: {ann.summer_energy_share.mean()*100:.0f}% on average.", "",
         "| Year | Energy (TWh) | Peak (MW) | Peak date | Hours within 10% of the peak |", "|---|---|---|---|---|"]
    for y, r in ann.iterrows():
        L.append(f"| {y} | {r.energy_TWh:.0f} | {r.peak_MW:,.0f} | {r.peak_date} | {r.hours_above_90pct_peak} |")
    L += ["", "## 2. How demand rises with heat (summer days, growth held fixed by year)", "",
          "| Relationship | Per degree F | As % of the 2018 summer average | Fit (R squared) |", "|---|---|---|---|",
          f"| Daily peak vs high, below 95 F | {f1['MW_per_F_below_95']:,.0f} MW (se {f1['se']:,.0f}) | {f1['pct_per_F_below_95']:.1f}% | {f1['r2']:.2f} |",
          f"| Daily peak vs high, 95 F and above | {f1['MW_per_F_above_95']:,.0f} MW (extra {f1['extra_MW_per_F_above_95']:+,.0f}, se {f1['se_extra']:,.0f}) | {f1['pct_per_F_above_95']:.1f}% | |",
          f"| Night low load vs daily low | {f2['MW_per_F']:,.0f} MW (se {f2['se']:,.0f}) | {f2['pct_per_F']:.1f}% | {f2['r2']:.2f} |",
          f"| Daily energy vs cooling degree days | {f3['MWh_per_cdd']:,.0f} MWh per cdd (se {f3['se']:,.0f}) | {f3['pct_per_cdd']:.1f}% per cdd | {f3['r2']:.2f} |",
          "", f"- Summer days analysed: {len(s):,}; days with a weighted Texas high of 95 F or more: {len(hot):,} "
          f"({len(hot)/len(s)*100:.0f}%).",
          f"- 2018 averages: summer daily peak {mean_peak_2018:,.0f} MW, overnight low {mean_low_2018:,.0f} MW, daily energy {mean_energy_2018/1e3:,.0f} GWh.",
          "", "## Limits", "",
          "- Load is what customers drew, not what they would have drawn: on emergency days (August 2011) some demand was cut.",
          "- Year effects absorb growth but also any other year-to-year change; the weather slopes assume the same response every year.",
          "- Airport temperatures; three zones (EAST, FWEST, NORTH) have no challenge station."]
    (OUT / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
