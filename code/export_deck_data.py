"""Export the data behind the web slide deck (presentation/) from the policy analysis outputs.

Reads only data dated 2018 or earlier plus our forecast (submission.csv); no 2019-2025 observation goes into the
deck (the observed columns in outputs/grid_heat_days are left out). Run after the policy_grid_* scripts:

    python code/export_deck_data.py

Writes presentation/data/deck_data.js  (window.DECK_DATA = {...}), loaded by presentation/charts.js.

What each chart gets
  cities     one record per challenge city: households, state, region, and whether it is "in need":
               no-AC need     : 10%+ of homes without AC (Census LACE) and forecast cooling-required days rising
               cost need      : a low-income family of four over the affordable bar in its state (forecast years)
                                and 30+ cooling-required days or hot nights a year in the forecast
  weather    per year 1976-2025, U.S. (mean over cities) and each EIA region: cooling-required days (high >= 95 F),
             hot nights (low >= 75 F), cooling degree days, hottest day. 1976-2018 from the challenge data (valid
             years only); 2019-2025 our forecast (days and nights: delta method as in policy_grid_heat_days.py;
             cdd and hottest day: submission.csv).
  regions    summer daily peak demand by 2 F bins of the daily high, as % of the region's mean summer peak
             (EIA-930 2015-2018, outputs/grid_national/region_daily.csv), plus each region's % per F.
  afford     per state 2002-2018: low-income bill / affordable bar (1 person and 4 people), using the state's real
             price that year x 2015 low-income use (RECS), against the 2018 bar.
  national   per year 2002-2018: mean cooling degree days (challenge cities), residential use per customer and
             real price (EIA-861, all states).
  states     per state, forecast 2019-2025: cooling-required days, bill / bar (1 and 4 people), homes without AC.
"""
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
import policy_grid_heat_days as hd
import policy_grid_demand as gd
import policy_grid_prices as gp
import policy_grid_prices_national as gpn

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "presentation" / "data" / "deck_data.js"
FC = range(2019, 2026)


def r(x, d=2):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), d)


def weather_series(cities):
    train, cov = load_train()
    d18 = train[train.Year <= 2018]
    slopes = {}
    for col, avg, miss in (("tmax", "Avg Tmax", "Miss Tmax"), ("tmin", "Avg Tmin", "Miss Tmin")):
        ser = e2._window_series(d18, d18[avg].where(d18[miss] <= 10), 2018)
        slopes[col] = e5._shared_slope(ser, sorted(c for c, s in ser.items() if len(s) >= e2.MIN_VALID))
    daily = e5b.load_daily()
    rows = []
    for key, col, thr in (("days", "tmax", 95.0), ("nights", "tmin", 75.0)):
        g = hd.per_year_counts(daily, col, thr)
        g = g[g.Year.between(1976, 2018)][["ID", "Year", "per_yr"]].rename(columns={"per_yr": key})
        rows.append(g.set_index(["ID", "Year"]))
        # forecast per year (delta method, last 10 valid years up to 2018)
        ok = hd.per_year_counts(daily, col, thr)[["ID", "Year"]]
        x = daily.merge(ok, on=["ID", "Year"]).dropna(subset=[col])
        fc = []
        for c, gg in x.groupby("ID"):
            last = sorted(gg.Year.unique())[-10:]
            if len(last) < 10:
                continue
            piv = np.mean(last)
            per = [(gg.loc[gg.Year == y, col].to_numpy(), hd.days_in(y) / (gg.Year == y).sum()) for y in last]
            for Y in FC:
                fc.append({"ID": c, "Year": Y, key: float(np.mean([(t + slopes[col] * (Y - piv) >= thr).sum() * s for t, s in per]))})
        rows.append(pd.DataFrame(fc).set_index(["ID", "Year"]))
    flags = valid_flags(train, cov)
    a = train.assign(cdd=train.cdd.where(flags["cdd"]), hottest=train["Max Tmax"].where(flags["hottest_day_temp"]))
    a = a[a.Year.between(1976, 2018)].set_index(["ID", "Year"])[["cdd", "hottest"]]
    sub = pd.read_csv(ROOT / "submission.csv")
    sub = sub[sub.metric.isin(["cdd", "hottest_day_temp"])].pivot_table(index=["city_id", "year"], columns="metric", values="predicted_value")
    sub = sub.rename(columns={"hottest_day_temp": "hottest"}).rename_axis(["ID", "Year"])
    days = pd.concat([x for x in rows if "days" in x.columns])
    nights = pd.concat([x for x in rows if "nights" in x.columns])
    allm = days.join(nights, how="outer").join(pd.concat([a, sub[["cdd", "hottest"]]]), how="outer").reset_index()
    allm = allm.merge(cities[["city_id", "Region"]], left_on="ID", right_on="city_id", how="inner")
    out = {"years": list(range(1976, 2026)), "forecast_from": 2019, "series": {}}
    for name, g in [("US", allm)] + list(allm.groupby("Region")):
        m = g.groupby("Year")[["days", "nights", "cdd", "hottest"]].mean()
        out["series"][name] = {k: [r(m[k].get(y), 1) for y in out["years"]] for k in ("days", "nights", "cdd", "hottest")}
    return out


def region_curves():
    d = pd.read_csv(ROOT / "outputs" / "grid_national" / "region_daily.csv", parse_dates=["DATE"])
    d = d[d.DATE.dt.month.isin([6, 7, 8, 9])]
    sens = pd.read_csv(ROOT / "outputs" / "grid_national" / "sensitivity.csv").set_index("Region")
    out = []
    for reg, g in d.groupby("Region"):
        g = g.assign(idx=g.peak / g.groupby("Year").peak.transform("mean") * 100, bin=(g.tmax // 2 * 2 + 1))
        b = g.groupby("bin").idx.agg(["mean", "size"])
        b = b[b["size"] >= 8]
        out.append({"region": reg, "pct_per_F": r(sens.loc[reg, "pct_per_F_day"]), "r2": r(sens.loc[reg, "r2_day"]),
                    "pts": [[r(t, 0), r(v, 1)] for t, v in b["mean"].items()]})
    return out


def afford_and_national(li):
    years = range(2002, 2019)
    st = pd.concat([gpn.states_residential(y) for y in years], ignore_index=True)
    cpi = gp.cpi()
    st["price18"] = st.rev / st.mwh * 100 * st.year.map(lambda y: cpi[2018] / cpi[y])
    s18 = pd.read_csv(ROOT / "outputs" / "grid_prices_national" / "states.csv").set_index("state").dropna(subset=["bill_1", "bill_4"])
    afford = []
    for s, row in s18.iterrows():
        p = st[st.state == s].set_index("year").price18
        kwh1 = row.kwh_base_1 + row.kwh_cool_1
        kwh4 = row.kwh_base_4 + row.kwh_cool_4
        afford.append({"state": s, "x1": [r(p.get(y) / 100 * kwh1 / row.bar_1) for y in years],
                       "x4": [r(p.get(y) / 100 * kwh4 / row.bar_4) for y in years]})
    nat = st.groupby("year").apply(lambda g: pd.Series({"price": (g.rev.sum() / g.mwh.sum() * 100) * cpi[2018] / cpi[int(g.name)],
                                                        "kwh": g.mwh.sum() * 1e3 / g.cust.sum()}), include_groups=False)
    cdd, _ = gpn.state_cdd()
    cdd_us = cdd[cdd.Year.between(2002, 2018)].groupby("Year").cdd.mean()
    national = {"years": list(years), "cdd": [r(cdd_us.get(y), 0) for y in years],
                "kwh": [r(nat.kwh.get(y), 0) for y in years], "price": [r(nat.price.get(y), 2) for y in years]}
    return {"years": list(years), "states": afford}, national


def main():
    cities = gd.city_region_table()
    S = pd.read_csv(ROOT / "outputs" / "grid_projection_national" / "states.csv").set_index("state")
    ch = pd.read_csv(ROOT / "outputs" / "grid_heat_days" / "city_heat_days.csv").set_index("city_id")
    li = pd.read_csv(ROOT / "outputs" / "grid_prices_national" / "recs_low_income.csv", dtype={"size": str})

    city_recs = []
    for _, c in cities.iterrows():
        h = ch.loc[c.city_id] if c.city_id in ch.index else None
        days_b, days_f = (h.hot_days_base, h.hot_days_fc) if h is not None else (np.nan, np.nan)
        nights_f = h.hot_nights_fc if h is not None else np.nan
        st = S.loc[c.state] if c.state in S.index else None
        no_ac = c.no_ac_pct
        need_ac = bool(no_ac >= 10 and days_f > days_b)
        need_cost = bool(st is not None and st.x_bar_4_central > 1 and (days_f >= 30 or nights_f >= 30))
        reason = "no AC" if need_ac else ("cost of cooling" if need_cost else "")
        city_recs.append({"name": c.Name, "state": c.state, "region": c.Region, "households": r(c.households, 0),
                          "no_ac": r(no_ac, 1), "days_base": r(days_b, 1), "days_fc": r(days_f, 1), "nights_fc": r(nights_f, 1),
                          "x_bar_4": r(st.x_bar_4_central) if st is not None else None, "need": reason})
    afford, national = afford_and_national(li)
    states = [{"state": s, "days_fc": r(x.hot_days_fc, 1), "nights_fc": r(x.hot_nights_fc, 1), "x1": r(x.x_bar_1_central),
               "x4": r(x.x_bar_4_central), "no_ac": r(x.no_ac_pct, 1), "added4": r(x.added_bill_4, 0)} for s, x in S.iterrows()]
    data = {"generated_by": "code/export_deck_data.py", "cities": city_recs, "weather": weather_series(cities),
            "regions": region_curves(), "afford": afford, "national": national, "states": states}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("// Generated by code/export_deck_data.py. Do not edit by hand.\nwindow.DECK_DATA = " + json.dumps(data, separators=(",", ":")) + ";\n",
                   encoding="utf-8")
    n_need = sum(1 for c in city_recs if c["need"])
    print(f"wrote {OUT} ({OUT.stat().st_size/1024:.0f} KB): {len(city_recs)} cities ({n_need} in need), "
          f"{len(data['regions'])} regions, {len(afford['states'])} states")


if __name__ == "__main__":
    main()
