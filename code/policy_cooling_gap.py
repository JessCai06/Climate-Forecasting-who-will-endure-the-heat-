"""Policy analysis 3: the cooling gap. Where will homes without air conditioning meet heat they were not built for?

A. Cooling gap per city
   Heat they were not built for = days per year with a daily high at or above the city's own 1976-2005
   99th percentile (the threshold from code/policy_extremes.py, a stand-in for a design temperature).
   - FORECAST heat days, 2019-2025: our model, using only data up to 2018. Same delta method as the
     submitted cdd forecast (Experiment 5B): take the city's actual daily highs from its last 10 valid
     years (up to 2018), warm them by the shared Tmax slope x (year - those years' middle year), count days
     at or above the threshold. Observed 2019-2025 heat days (policy_extremes, analysis only) are shown
     next to it as a check, never used to make it.
   - Homes without AC: Census Local Air Conditioning Estimates (LACE) 2023, county of the station.
   Cooling gap = households without AC x forecast heat days per year ("uncooled household heat-days");
   and per household: share without AC x forecast heat days.

B. City archetypes
   k-means (k = 4, fixed before running; seed 42) on six standardized city features:
     share of homes without AC (LACE), forecast rise in heat days vs 1976-2005,
     impervious surface %, tree canopy %, poverty %, adults living alone %
   The last four are population-weighted means over the county's ZIP code areas from the CDC/ATSDR Heat &
   Health Index 2024 (NLCD 2021 land cover; ACS 2015-2019), so they describe where people live, not the
   county's empty land. Stability: the clustering is repeated with 50 seeds and agreement is reported.

None of these datasets is a forecast input: they sit on top of the forecast (code/AGENTS.md). Housing,
land cover and population do not respond to the weather, so their year does not matter for the data rule.

Run from the repo root:   python code/policy_cooling_gap.py
Downloads (cached in data/raw/policy/, not committed): LACE county file, the HHI table (ArcGIS service),
the Census 2010 ZCTA-to-county relationship file.
Writes outputs/cooling_gap/: config.json, city_cooling_gap.csv, summary.md
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shared import load_train, valid_flags
import exp02_line_forest as e2
import exp05_levels_slopes as e5
import exp05b_daily_distribution as e5b

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "policy"
OUT = ROOT / "outputs" / "cooling_gap"
LACE = "https://www2.census.gov/programs-surveys/demo/datasets/lace/2023/LACE_23_County.csv"
REL = "https://www2.census.gov/geo/docs/maps-data/data/rel/zcta_county_rel_10.txt"
HHI = ("https://onemap.cdc.gov/onemapservices/rest/services/Hosted/The_Heat_And_Health_Index/FeatureServer/0/query"
       "?where=1%3D1&outFields=zcta5ce10,pop,p_imperv,p_treec,p_pov,p_iso,p_age65,pr_hri"
       "&returnGeometry=false&orderByFields=objectid&resultOffset={}&resultRecordCount=2000&f=json")
CFG = {"k": 4, "seed": 42, "stability_seeds": 50, "recent_years_for_days": 10, "forecast_years": [2019, 2025],
       "features": ["no_ac_pct", "heat_days_rise_fc", "imperv_pct", "canopy_pct", "poverty_pct", "alone_pct"]}


def cached(name, url):
    p = RAW / name
    if not p.exists():
        RAW.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, p)
    return p


def load_hhi():
    p = RAW / "hhi_zcta.csv"
    if p.exists():
        return pd.read_csv(p, dtype={"zcta5ce10": str})
    rows, off = [], 0
    while True:
        for attempt in range(4):
            try:
                with urllib.request.urlopen(HHI.format(off), timeout=120) as r:
                    feats = json.loads(r.read().decode())["features"]
                break
            except Exception:
                time.sleep(5 * (attempt + 1))
        else:
            raise RuntimeError(f"HHI download failed at offset {off}")
        if not feats:
            break
        rows += [f["attributes"] for f in feats]
        off += len(feats)
    df = pd.DataFrame(rows)
    RAW.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False)
    return df


def county_features():
    lace = pd.read_csv(cached("lace_2023_county.csv", LACE), dtype={"STATE": str, "COUNTY": str})
    lace["county_fips"] = lace.STATE + lace.COUNTY
    lace = lace.rename(columns={"NO_AC_PE": "no_ac_pct", "NO_AC_E": "no_ac_households", "HSE_OCC_E": "households",
                                "NO_AC_PM": "no_ac_pct_moe"})[["county_fips", "households", "no_ac_households",
                                                               "no_ac_pct", "no_ac_pct_moe"]]
    hhi = load_hhi()
    hhi = hhi.replace(-999, np.nan)
    rel = pd.read_csv(cached("zcta_county_rel_10.txt", REL), dtype={"ZCTA5": str, "GEOID": str})
    m = rel[["ZCTA5", "GEOID", "POPPT"]].merge(hhi, left_on="ZCTA5", right_on="zcta5ce10")
    cols = {"p_imperv": "imperv_pct", "p_treec": "canopy_pct", "p_pov": "poverty_pct", "p_iso": "alone_pct",
            "p_age65": "age65_pct", "pr_hri": "heat_illness_rank"}
    out = {}
    for c, g in m.groupby("GEOID"):
        w = g.POPPT.to_numpy(float)
        rec = {}
        for src, dst in cols.items():
            v = g[src].to_numpy(float)
            ok = ~np.isnan(v) & (w > 0)
            rec[dst] = float(np.average(v[ok], weights=w[ok])) if ok.any() else np.nan
        out[c] = rec
    hh = pd.DataFrame(out).T.rename_axis("county_fips").reset_index()
    return lace.merge(hh, on="county_fips", how="left")


def forecast_heat_days(thr):
    """Forecast days/yr at or above `thr` (dict city -> F) for 2019-2025, delta method on daily highs <= 2018."""
    train, cov = load_train()
    d = train[train.Year <= 2018]
    tx = e2._window_series(d, d["Avg Tmax"].where(d["Miss Tmax"] <= 10), 2018)
    slope = e5._shared_slope(tx, sorted(c for c, s in tx.items() if len(s) >= e2.MIN_VALID))
    daily = e5b.load_daily()
    daily = daily[daily.Year <= 2018].dropna(subset=["tmax"])
    ok = d[d["Miss Tmax"] <= 10][["ID", "Year"]]
    daily = daily.merge(ok, on=["ID", "Year"])
    yrs_fc = np.arange(CFG["forecast_years"][0], CFG["forecast_years"][1] + 1)
    out = {}
    for c, g in daily.groupby("ID"):
        if c not in thr:
            continue
        last = sorted(g.Year.unique())[-CFG["recent_years_for_days"]:]
        if len(last) < CFG["recent_years_for_days"]:
            continue
        piv = np.mean(last)
        per_year = [(g[g.Year == y].tmax.to_numpy(), 365.25 / (g.Year == y).sum()) for y in last]
        fc = [np.mean([(t + slope * (Y - piv) >= thr[c]).sum() * scale for t, scale in per_year]) for Y in yrs_fc]
        out[c] = float(np.mean(fc))
    return pd.Series(out, name="heat_days_fc"), slope


def archetypes(df):
    X = df[CFG["features"]].astype(float)
    Z = ((X - X.mean()) / X.std()).to_numpy()

    def kmeans(seed):
        rng = np.random.default_rng(seed)
        cent = Z[rng.choice(len(Z), CFG["k"], replace=False)]
        for _ in range(300):
            lab = np.argmin(((Z[:, None, :] - cent[None]) ** 2).sum(-1), axis=1)
            new = np.array([Z[lab == j].mean(0) if (lab == j).any() else cent[j] for j in range(CFG["k"])])
            if np.allclose(new, cent):
                break
            cent = new
        return lab, ((Z - cent[lab]) ** 2).sum()

    # best of several starts for the main solution (deterministic: seeds 42..)
    runs = [kmeans(CFG["seed"] + i) for i in range(CFG["stability_seeds"])]
    best = min(runs, key=lambda r: r[1])[0]

    def agree(a, b):   # share of city pairs grouped the same way in both labelings (Rand index)
        sa, sb = a[:, None] == a[None], b[:, None] == b[None]
        iu = np.triu_indices(len(a), 1)
        return float((sa[iu] == sb[iu]).mean())
    stab = float(np.mean([agree(best, r[0]) for r in runs]))
    return best, stab


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "config.json").write_text(json.dumps(CFG, indent=2))            # before any result
    ext = pd.read_csv(ROOT / "outputs" / "policy_extremes" / "city_extremes.csv")
    sc = pd.read_csv(ROOT / "outputs" / "policy_check" / "station_county.csv", dtype=str)
    thr = ext.set_index("city_id").heat_threshold_F.to_dict()
    fc, slope = forecast_heat_days(thr)
    cf = county_features()

    df = (ext[["city_id", "Name", "Lat", "Lon", "heat_threshold_F", "heat_days_per_yr_base", "heat_days_per_yr_recent"]]
          .merge(sc[["ID", "county_fips", "county_name", "state"]], left_on="city_id", right_on="ID")
          .merge(cf, on="county_fips", how="left").drop(columns="ID"))
    df["heat_days_fc"] = df.city_id.map(fc)
    df = df.rename(columns={"heat_days_per_yr_base": "heat_days_1976_2005", "heat_days_per_yr_recent": "heat_days_obs_2019_2025"})
    df["heat_days_rise_fc"] = df.heat_days_fc - df.heat_days_1976_2005
    df["gap_per_household"] = df.no_ac_pct / 100 * df.heat_days_fc                  # uncooled heat-days per household
    df["gap_households"] = df.no_ac_households * df.heat_days_fc                     # uncooled household heat-days
    df["gap_added_households"] = df.no_ac_households * df.heat_days_rise_fc.clip(lower=0)
    df = df.dropna(subset=CFG["features"]).reset_index(drop=True)
    lab, stab = archetypes(df)
    df["archetype"] = lab
    df.to_csv(OUT / "city_cooling_gap.csv", index=False, float_format="%.3f")

    # ------------------------------------------------------------------ summary
    prof = df.groupby("archetype").agg(cities=("city_id", "size"), median_lat=("Lat", "median"),
                                       **{f: (f, "median") for f in CFG["features"]},
                                       heat_days_fc=("heat_days_fc", "median"),
                                       heat_days_obs=("heat_days_obs_2019_2025", "median"),
                                       uncooled_households=("no_ac_households", "sum"))
    r_fc_obs = df[["heat_days_fc", "heat_days_obs_2019_2025"]].corr(method="spearman").iloc[0, 1]
    L = ["# The cooling gap: homes without AC meeting heat they were not built for", "",
         f"Cities: {len(df)}. Heat threshold = each city's 1976-2005 99th percentile of daily highs. "
         f"Forecast heat days use data up to 2018 only (delta method, shared Tmax slope {slope:.4f} F/yr). "
         "Homes without AC: Census LACE 2023 (experimental). Built environment and people: CDC/ATSDR Heat & Health Index 2024.", "",
         f"Check of the forecast against what happened (analysis only): median heat days/yr 1976-2005 "
         f"{df.heat_days_1976_2005.median():.1f}, forecast 2019-2025 {df.heat_days_fc.median():.1f}, observed "
         f"{df.heat_days_obs_2019_2025.median():.1f}; rank correlation forecast vs observed across cities {r_fc_obs:.2f}.", "",
         "## A. Largest cooling gaps per household (share without AC x forecast heat days/yr)", "",
         "| City | County | No AC % | Heat days/yr 1976-2005 | Forecast 2019-25 | Observed 2019-25 | Uncooled heat-days per household | Households without AC |",
         "|---|---|---|---|---|---|---|---|"]
    for r in df.sort_values("gap_per_household", ascending=False).head(15).itertuples():
        L.append(f"| {r.Name} | {r.county_name}, {r.state} | {r.no_ac_pct:.1f} | {r.heat_days_1976_2005:.1f} | {r.heat_days_fc:.1f} | "
                 f"{r.heat_days_obs_2019_2025:.1f} | {r.gap_per_household:.2f} | {r.no_ac_households:,.0f} |")
    L += ["", "## A. Largest totals (households without AC x forecast heat days/yr)", "",
          "| City | County | Households without AC | Forecast heat days/yr | Uncooled household heat-days/yr |", "|---|---|---|---|---|"]
    for r in df.sort_values("gap_households", ascending=False).head(10).itertuples():
        L.append(f"| {r.Name} | {r.county_name}, {r.state} | {r.no_ac_households:,.0f} | {r.heat_days_fc:.1f} | {r.gap_households:,.0f} |")
    L += ["", f"## B. Archetypes (k-means, k = {CFG['k']}; agreement across {CFG['stability_seeds']} starts: {stab:.0%})", "",
          "| Archetype | Cities | Median lat | No AC % | Heat-day rise (fc) | Impervious % | Canopy % | Poverty % | Living alone % | Households without AC (sum) | Example cities |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for a, p in prof.iterrows():
        ex = ", ".join(df[df.archetype == a].sort_values("gap_per_household", ascending=False).Name.head(6))
        L.append(f"| {a} | {p.cities} | {p.median_lat:.1f} | {p.no_ac_pct:.1f} | {p.heat_days_rise_fc:+.1f} | {p.imperv_pct:.0f} | "
                 f"{p.canopy_pct:.0f} | {p.poverty_pct:.0f} | {p.alone_pct:.0f} | {p.uncooled_households:,.0f} | {ex} |")
    (OUT / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
