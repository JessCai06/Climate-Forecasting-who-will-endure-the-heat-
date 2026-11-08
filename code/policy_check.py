"""Policy heuristic check: are older small mixed-use / small multifamily buildings in cities whose heat has moved
past their design assumptions, and are they left out of the rules? (analysis only, not a forecast)

Thesis, split into three claims per city (thresholds fixed in CONFIG and written to config.json BEFORE any result):
  H1 hazard   : 2019-2025 heat has moved past the 1976-2005 design baseline
  H2 exposure : the city's county has an above-median share of older small multifamily housing (ACS proxy)
  H3 policy   : no in-force (by 2025) rental cooling rule that covers small mixed-use buildings
Supported if at least CONFIG["support_min_share"] of cities have all three.

Weather input: by default the OBSERVED 2019-2025 NOAA data (obs_2018_2021.csv + obs_2021_2025.csv, user-approved
stand-in, analysis only). Swap in the forecast with  --weather submission.csv  (same columns).

Run from the repo root (after python code/census_acs.py and python code/policy_case_studies.py):
    python code/policy_check.py [--weather FILE]
Outputs: outputs/policy_check/ (config.json first, then weather_input.csv, station_county.csv, city_flags.csv,
sensitivity.csv, thesis_check.md, charts/flags_map.png)
"""
import argparse
import calendar
import concurrent.futures as cf
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shared import METRICS, load_train, valid_flags

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs" / "policy_check"
OBS_FILES = [ROOT / "obs_2018_2021.csv", ROOT / "obs_2021_2025.csv"]
YEARS = list(range(2019, 2026))

CONFIG = {
    "baseline_years": [1976, 2005],            # roughly the TMY3 period buildings were designed with
    "baseline_min_valid_years": 15,
    "weather_years": [2019, 2025],
    "weather_min_valid_years": 4,
    "max_missing_days": 10,                    # same validity rule as the challenge
    "indoor_limit_F": 80,                      # main indoor heat limit (Phoenix 82, Montgomery Co. MD 80, NYC 78)
    "indoor_limit_sensitivity_F": [78, 80, 82],
    "h1_cdd_increase_min": 0.10,               # cdd at least 10% above baseline ...
    "h1_hottest_increase_min_F": 2.0,          # ... AND hottest day at least 2 F above baseline
    "h1_shortfall_min": 0.10,                  # OR cooling capacity shortfall at least 10%
    "shortfall_min_design_gap_F": 5.0,         # shortfall not computed if baseline hottest day < indoor limit + 5 F
    "h2_rule": "exposure = share of units in 2-19 unit buildings x share of units built before 1980 (county); "
               "flag if >= median across the cities",
    "h3_rule": "gap unless data/policy_rules.csv lists an in_force cooling rule with covers_small_mixed_use yes/partial",
    "support_min_share": 0.20,                 # thesis supported if >= 20% of cities have H1, H2 and H3
    "shortfall_formula": "(T_hot_new - T_in) / (T_hot_design - T_in) - 1; steady-state, ignores sun, people, "
                         "equipment and humidity",
}


# ------------------------------------------------------------------ weather
def observed_weather():
    """Observed 2019-2025 annual metrics in submission schema (city_id, year, metric, predicted_value), valid years only."""
    obs = pd.concat([pd.read_csv(f) for f in OBS_FILES]).drop_duplicates(["ID", "DATE"])
    obs = obs[obs.DATE.str[:4].astype(int).between(YEARS[0], YEARS[-1])].copy()
    obs["year"] = obs.DATE.str[:4].astype(int)
    f = lambda v: v / 10 * 9 / 5 + 32                                    # tenths of degC -> F (as code/truth.py)
    obs["tmax"], obs["tmin"] = f(obs.TMAX), f(obs.TMIN)
    obs["tavg"] = (obs.tmax + obs.tmin) / 2
    obs["cddd"] = np.maximum(0, obs.tavg - 65)
    obs["prcp"] = obs.PRCP / 254.0
    g = obs.groupby(["ID", "year"])
    a = pd.DataFrame({"avg": g.tavg.mean(), "hot": g.tmax.max().round(), "cdd": g.cddd.sum(), "prcp": g.prcp.sum(),
                      "n_tmax": g.tmax.count(), "n_tmin": g.tmin.count(), "n_both": g.tavg.count(),
                      "n_prcp": g.prcp.count()}).reset_index()
    days = a.year.map(lambda y: 366 if calendar.isleap(y) else 365)
    lim = CONFIG["max_missing_days"]
    ok = {"annual_avg_temp": (days - np.minimum(a.n_tmax, a.n_tmin)) <= lim, "hottest_day_temp": (days - a.n_tmax) <= lim,
          "cdd": (days - a.n_both) <= lim, "total_precip_in": (days - a.n_prcp) <= lim}
    col = {"annual_avg_temp": "avg", "hottest_day_temp": "hot", "cdd": "cdd", "total_precip_in": "prcp"}
    rows = [pd.DataFrame({"city_id": a.ID[ok[m]], "year": a.year[ok[m]], "metric": m, "predicted_value": a[col[m]][ok[m]]})
            for m in col]
    return pd.concat(rows, ignore_index=True).sort_values(["city_id", "metric", "year"])


def weather_means(w):
    """Mean over 2019-2025 per city and metric, requiring the minimum number of valid years."""
    w = w[w.year.between(*CONFIG["weather_years"])]
    g = w.groupby(["city_id", "metric"]).predicted_value
    m = g.mean().where(g.count() >= CONFIG["weather_min_valid_years"])
    return m.unstack("metric")


def baseline(train_df, cov):
    lo, hi = CONFIG["baseline_years"]
    flags = valid_flags(train_df, cov)
    out = {}
    for metric, col in METRICS.items():
        v = train_df[col].where(flags[metric] & train_df.Year.between(lo, hi))
        g = v.groupby(train_df.ID)
        out[metric] = g.mean().where(g.count() >= CONFIG["baseline_min_valid_years"])
    return pd.DataFrame(out)


# ------------------------------------------------------------------ buildings
def station_county(cities, path):
    if path.exists():
        cached = pd.read_csv(path, dtype={"county_fips": str})
        if set(cached.ID) == set(cities.index):
            return cached

    def one(item):
        i, (lat, lon) = item
        url = f"https://geo.fcc.gov/api/census/block/find?latitude={lat}&longitude={lon}&format=json"
        for attempt in range(4):
            try:
                with urllib.request.urlopen(url, timeout=30) as r:
                    d = json.loads(r.read().decode())
                break
            except (TimeoutError, OSError):
                if attempt == 3:
                    raise
        return {"ID": i, "county_fips": d["County"]["FIPS"], "county_name": d["County"]["name"], "state": d["State"]["code"]}

    with cf.ThreadPoolExecutor(4) as ex:
        rows = list(ex.map(one, [(i, (r.Lat, r.Lon)) for i, r in cities.iterrows()]))
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    return df


def acs_exposure(path):
    a = pd.read_csv(path, dtype={"county_fips": str})
    tot_u, tot_y, tot_t = a.B25024_001E, a.B25034_001E, a.B25003_001E
    a["share_small_mf"] = a[["B25024_004E", "B25024_005E", "B25024_006E", "B25024_007E"]].sum(axis=1) / tot_u   # 2-19 units
    a["share_pre1980"] = a[[f"B25034_{i:03d}E" for i in range(7, 12)]].sum(axis=1) / tot_y                     # built <1980
    a["share_renter"] = a.B25003_003E / tot_t
    a["units_small_mf"] = a[["B25024_004E", "B25024_005E", "B25024_006E", "B25024_007E"]].sum(axis=1)
    a["exposure"] = a.share_small_mf * a.share_pre1980
    return a[["county_fips", "NAME", "units_small_mf", "share_small_mf", "share_pre1980", "share_renter", "exposure"]]


def policy_gap(names):
    r = pd.read_csv(ROOT / "data" / "policy_rules.csv")
    cool = r[(r.rule_type == "cooling") & (r.status_2025 == "in_force") & r.covers_small_mixed_use.isin(["yes", "partial"])]
    covered = set(cool.city_name)
    checked = set(r.city_name)
    status = names.map(lambda n: "covered" if n in covered else ("gap (checked)" if n in checked else "gap (not checked)"))
    return status


# ------------------------------------------------------------------ flags
def shortfall(hot_new, hot_base, t_in):
    gap = hot_base - t_in
    s = (hot_new - t_in) / gap - 1
    s = s.where(gap >= CONFIG["shortfall_min_design_gap_F"])
    return s.clip(lower=0)


def flags(df, t_in):
    sf = shortfall(df.hot_new, df.hot_base, t_in)
    h1 = ((df.cdd_change >= CONFIG["h1_cdd_increase_min"]) & (df.hot_change >= CONFIG["h1_hottest_increase_min_F"])) \
        | (sf >= CONFIG["h1_shortfall_min"])
    h1 = h1.where(df.cdd_base.notna() & df.cdd_new.notna() & df.hot_base.notna() & df.hot_new.notna())
    h2 = df.exposure >= df.exposure.median()
    h3 = df.policy_status != "covered"
    return sf, h1, h2, h3


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--weather", default=None, help="submission-schema CSV (default: observed NOAA 2019-2025)")
    a = ap.parse_args(argv)
    (OUT / "charts").mkdir(parents=True, exist_ok=True)
    weather_label = "forecast: " + a.weather if a.weather else "OBSERVED NOAA GHCN-Daily 2019-2025 (stand-in, analysis only)"
    (OUT / "config.json").write_text(json.dumps({**CONFIG, "weather_input": weather_label,
                                                 "written_utc": datetime.now(timezone.utc).isoformat()}, indent=2))

    train_df, cov = load_train()
    cities = train_df.groupby("ID")[["Name", "Lat", "Lon"]].first()
    if a.weather:
        w = pd.read_csv(a.weather)
    else:
        w = observed_weather()
        w.to_csv(OUT / "weather_input.csv", index=False)
    new, base = weather_means(w), baseline(train_df, cov)
    sc = station_county(cities, OUT / "station_county.csv")
    acs = acs_exposure(OUT / "acs_county_2023.csv")

    df = cities.join(base.add_suffix("_base")).join(new.add_suffix("_new"))
    df = df.rename(columns={"cdd_base": "cdd_base", "hottest_day_temp_base": "hot_base", "hottest_day_temp_new": "hot_new",
                            "annual_avg_temp_base": "avg_base", "annual_avg_temp_new": "avg_new"})
    df = df[["Name", "Lat", "Lon", "avg_base", "avg_new", "cdd_base", "cdd_new", "hot_base", "hot_new"]]
    df["cdd_change"] = df.cdd_new / df.cdd_base - 1          # ~ % change in cooling energy (degree-day method)
    df["hot_change"] = df.hot_new - df.hot_base
    df = df.join(sc.set_index("ID")).reset_index().merge(acs, on="county_fips", how="left").set_index("ID")
    df["policy_status"] = policy_gap(df.Name)

    sens = []
    for t in CONFIG["indoor_limit_sensitivity_F"]:
        sf, h1, h2, h3 = flags(df, t)
        allf = (h1 == True) & h2 & h3
        sens.append({"indoor_limit_F": t, "n_cities": len(df), "n_h1_evaluable": int(h1.notna().sum()),
                     "n_h1": int((h1 == True).sum()), "n_h2": int(h2.sum()), "n_h3": int(h3.sum()),
                     "n_all_three": int(allf.sum()), "share_all_three": allf.sum() / len(df),
                     "supported": bool(allf.sum() / len(df) >= CONFIG["support_min_share"])})
        if t == CONFIG["indoor_limit_F"]:
            df["shortfall"], df["H1"], df["H2"], df["H3"] = sf, h1, h2, h3
            df["all_three"] = allf
    sens = pd.DataFrame(sens)
    df.round(4).to_csv(OUT / "city_flags.csv")
    sens.to_csv(OUT / "sensitivity.csv", index=False)
    write_report(df, sens, weather_label)
    chart(df)
    print(sens.to_string(index=False))
    print("wrote", OUT)


# ------------------------------------------------------------------ report
def write_report(df, sens, weather_label):
    main = sens[sens.indoor_limit_F == CONFIG["indoor_limit_F"]].iloc[0]
    n = len(df)
    ev = df[df.H1.notna()]
    cs = pd.read_csv(OUT / "case_studies.csv") if (OUT / "case_studies.csv").exists() else None
    top = df[df.all_three].sort_values("cdd_change", ascending=False)
    h1_not_h2 = df[(df.H1 == True) & ~df.H2]
    h2_not_h1 = df[(df.H1 == False) & df.H2]
    fmt = lambda s: ", ".join(s) if len(s) else "none"
    L = [
        "# Policy heuristic check",
        "",
        f"Weather input: **{weather_label}**. Thresholds were fixed in `config.json` before the results were computed.",
        "",
        "## Verdict",
        "",
        f"- Cities with all three flags (heat past design, older small multifamily stock, no cooling rule): "
        f"**{int(main.n_all_three)} of {n} ({main.share_all_three:.0%})**. Threshold for 'supported': "
        f"{CONFIG['support_min_share']:.0%}. **Thesis {'supported' if main.supported else 'NOT supported'}** "
        f"at an indoor limit of {CONFIG['indoor_limit_F']} F.",
        "- Indoor limit sensitivity: " + "; ".join(f"{int(r.indoor_limit_F)} F: {int(r.n_all_three)} cities "
                                                    f"({'supported' if r.supported else 'not supported'})"
                                                    for r in sens.itertuples()) + ".",
        "",
        "## The three claims",
        "",
        "| Claim | Cities flagged | Evaluable |",
        "|---|---|---|",
        f"| H1 heat past design (1976-2005 baseline) | {int(main.n_h1)} | {int(main.n_h1_evaluable)} |",
        f"| H2 above-median older small multifamily share (by construction about half) | {int(main.n_h2)} | {n} |",
        f"| H3 no in-force rental cooling rule covering small buildings | {int(main.n_h3)} | {n} (checked by hand for 9 cities) |",
        "",
        f"Across the {len(ev)} cities with enough data: median cdd change {ev.cdd_change.median():+.0%}, "
        f"median hottest-day change {ev.hot_change.median():+.1f} F; cdd rose in {(ev.cdd_change > 0).mean():.0%} of them "
        f"and the hottest day rose in {(ev.hot_change > 0).mean():.0%}.",
        "",
        "## Post-hoc breakdown (looked at after the verdict; does not change it)",
        "",
        f"- Cooling **energy** claim alone (cdd at least 10% above baseline, baseline cdd at least 100): "
        f"{int(((df.cdd_change >= 0.10) & (df.cdd_base >= 100)).sum())} cities; with H2 and H3 as well: "
        f"{int(((df.cdd_change >= 0.10) & (df.cdd_base >= 100) & df.H2 & df.H3).sum())}.",
        f"- **Peak** heat claim alone: hottest day at least 2 F above baseline in {int((df.hot_change >= 2).sum())} cities; "
        f"capacity shortfall at least 10% in {int((df.shortfall >= 0.10).sum())}.",
        f"- H1 rate among cities with above-median older small multifamily stock: {(ev[ev.H2].H1 == True).mean():.0%}; "
        f"among the rest: {(ev[~ev.H2].H1 == True).mean():.0%}.",
        "",
        "## Cities with all three flags (largest cooling-load increase first)",
        "",
        "| City | County | cdd 1976-2005 | cdd 2019-2025 | Cooling load change | Hottest day change F | Capacity shortfall | Small MF share | Pre-1980 share |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for i, r in top.head(25).iterrows():
        sf = "n/a" if pd.isna(r.shortfall) else f"{r.shortfall:.0%}"
        L.append(f"| {r.Name} | {r.county_name}, {r.state} | {r.cdd_base:.0f} | {r.cdd_new:.0f} | {r.cdd_change:+.0%} | "
                 f"{r.hot_change:+.1f} | {sf} | {r.share_small_mf:.0%} | {r.share_pre1980:.0%} |")
    if len(top) > 25:
        L.append(f"| ... {len(top) - 25} more in `city_flags.csv` | | | | | | | | |")
    L += [
        "",
        "## Evidence against the thesis",
        "",
        f"- Heat past design but **little** older small multifamily stock ({len(h1_not_h2)}): {fmt(h1_not_h2.Name.head(20).tolist())}"
        + (" ..." if len(h1_not_h2) > 20 else ""),
        f"- Lots of older small multifamily stock but heat **not** past design ({len(h2_not_h1)}): {fmt(h2_not_h1.Name.head(20).tolist())}"
        + (" ..." if len(h2_not_h1) > 20 else ""),
        f"- Cities with a cooling rule in force: {fmt(df[df.policy_status == 'covered'].Name.tolist())}",
        "",
    ]
    if cs is not None:
        L += ["## Case studies (actual mixed-use buildings)", "",
              "| City | Mixed-use buildings | Year built recorded | Built before 1980 | Below size limit of building rules | Central AC |",
              "|---|---|---|---|---|---|"]
        for r in cs.itertuples():
            p = lambda x: "n/a" if pd.isna(x) else f"{x:.0%}"
            L.append(f"| {r.city_name} | {r.n_mixed_use:,} | {p(r.share_with_year_built)} | {p(r.share_pre1980_of_known)} | "
                     f"{p(r.share_below_bps_size)} (limit {r.bps_size_threshold_sqft:,} sq ft) | {p(r.share_central_ac_of_known)} |")
        L.append("")
        for c in ["Pittsburgh", "NewYork", "Chicago"]:
            if c in set(df.Name):
                r = df[df.Name == c].iloc[0]
                L.append(f"- **{c}**: cdd {r.cdd_base:.0f} -> {r.cdd_new:.0f} ({r.cdd_change:+.0%}), hottest day "
                         f"{r.hot_base:.1f} -> {r.hot_new:.1f} F; H1 {bool(r.H1 == True)}, H2 {bool(r.H2)}, H3 {r.policy_status}.")
        L.append("")
    L += [
        "## Method limits (state these with any result)",
        "",
        "- H1 compares 2019-2025 with 1976-2005 at the station. Most stations are at airports, outside the dense "
        "centres where mixed-use buildings are, so heat there is probably understated (urban heat island).",
        f"- Capacity shortfall uses {CONFIG['shortfall_formula']}. The design temperature is approximated by the mean "
        "annual hottest day, not the ASHRAE 0.4%/1% design values (copyrighted).",
        "- Cooling load change uses the degree-day method: cooling energy taken as proportional to cdd.",
        "- H2 is a county proxy: ACS counts building size and age, not mixed use, and cannot cross them "
        "(exposure = product of the two shares). The station's county may differ from the city's.",
        "- H3 relies on reported rules (data/policy_rules.csv); most cities were not checked in their municipal code, "
        "so 'gap (not checked)' means no rule was found in national reporting, not that none exists.",
        "- The weather input is observed data used as a stand-in for the forecast; rerun with `--weather submission.csv`.",
    ]
    (OUT / "thesis_check.md").write_text("\n".join(L), encoding="utf-8")


def chart(df):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(11, 6.5))
    cats = [("No heat flag / no data", (df.H1 != True), "#c9c9c9", 18),
            ("Heat past design only", (df.H1 == True) & ~(df.H2 & df.H3), "#f2a65a", 30),
            ("Heat + older small multifamily + no cooling rule", df.all_three, "#c0392b", 46)]
    for label, m, c, s in cats:
        ax.scatter(df.Lon[m], df.Lat[m], s=s, c=c, label=f"{label} ({int(m.sum())})", edgecolors="white", linewidths=0.5)
    for c in ["Pittsburgh", "NewYork", "Chicago", "Phoenix", "Houston"]:
        r = df[df.Name == c]
        if len(r):
            ax.annotate(c, (r.Lon.iloc[0], r.Lat.iloc[0]), xytext=(4, 4), textcoords="offset points", fontsize=8)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(f"Policy heuristic check, {len(df)} cities (indoor limit {CONFIG['indoor_limit_F']} F)")
    ax.legend(loc="lower left", fontsize=9, frameon=False)
    ax.set_aspect(1.25)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "charts" / "flags_map.png", dpi=150)


if __name__ == "__main__":
    main()
