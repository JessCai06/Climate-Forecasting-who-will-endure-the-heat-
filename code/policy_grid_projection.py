"""Policy essay, section 5: put weather, grid and prices together for 2019-2025. Lead case: ERCOT / Texas.

Everything here is made with data up to 2018 (code/AGENTS.md). No 2019-2025 observation is read.

A. Grid strain (2019-2023, the years ERCOT's December 2018 plan covers)
   ERCOT's plan (Capacity, Demand and Reserves report, Dec 2018) gives each summer's peak demand "based on normal
   weather", firm load and total capacity. Normal weather is past weather; it does not include warming.
   We add the warming our forecast expects:
     - weather draws: the 15 summers 2004-2018 of the zone-weighted Texas daily highs (outputs/grid_ercot)
     - a draw from summer y, used for year Y, is warmed by the shared Tmax slope x (Y - y)   (delta method)
     - each summer is run through the section 3 model (daily peak vs high, growth held at 2018) and its highest
       day kept; "normal" = the same draws unwarmed
     - warming effect(Y) = mean warmed annual peak - mean normal annual peak   (an average summer)
       hot-summer effect(Y) = the 90th percentile warmed draw - mean normal       (about one summer in ten)
   Peak(Y) = ERCOT's normal-weather peak(Y) + effect(Y). Reserve margin = (capacity - firm load) / firm load,
   with firm load = peak - ERCOT's own load reductions (peak minus firm load in its plan).

B. Bills for a poverty-line household (2019-2025, 2018 dollars)
   - Use: Southern households earning under $20,000, RECS 2015: 10,829 kWh, of which 2,460 kWh cooling.
     Cooling use scales with Texas cooling degree days: cooling(Y) = 2,460 x cdd(Y) / cdd(2015).
     cdd(Y) is our submitted forecast (submission.csv), zone-weighted like section 3; cdd(2015) is the
     zone-weighted 2015 value from the challenge data (RECS 2015's own weather year).
   - Price: 2018 Texas price, 11.20 cents (section 4). Scarcity case: + the 2016-2018 rise in ERCOT's average
     wholesale price ($24.62 -> $35.63 per MWh, Potomac Economics) passed through in full: +1.10 cents.
   - Bar: section 4 (Texas): $622 (1 person) and $1,287 (4 people) a year.
   - Cooling the bar allows: bar / price - non-cooling use, against the cooling the weather calls for.

Run from the repo root (after policy_grid_ercot.py and policy_grid_prices.py):
    python code/policy_grid_projection.py
Writes outputs/grid_projection/: config.json, grid.csv, bills.csv, summary.md
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
import policy_grid_ercot as ge

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs" / "grid_projection"
CFG = {
    "draw_years": [2004, 2018], "forecast_years": [2019, 2025], "hot_quantile": 0.9,
    "ercot_cdr_dec2018": {   # ERCOT Capacity, Demand and Reserves report, 4 Dec 2018, summer summary
        "years": [2019, 2020, 2021, 2022, 2023],
        "peak_normal_weather_MW": [74853, 76845, 78824, 80455, 82101],
        "firm_peak_load_MW": [72674, 74686, 76664, 78295, 79942],
        "total_capacity_MW": [78555, 82652, 86016, 85958, 85958],
        "reserve_margin_reported": [0.081, 0.107, 0.122, 0.098, 0.075],
        "target_reserve_margin": 0.1375},
    "kwh_total": 10829, "kwh_cooling": 2460,            # RECS 2015 CE4.9, South, income < $20,000
    "price_c_kwh_2018": 11.20, "scarcity_adder_c_kwh": (35.63 - 24.62) / 10,
    "bar": {"1": 622.0, "4": 1287.0}, "income": {"1": 12140, "4": 25100},
}


def tmax_slope():
    train, _ = load_train()
    d = train[train.Year <= 2018]
    ser = e2._window_series(d, d["Avg Tmax"].where(d["Miss Tmax"] <= 10), 2018)
    return e5._shared_slope(ser, sorted(c for c, s in ser.items() if len(s) >= e2.MIN_VALID)), train


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "config.json").write_text(json.dumps(CFG, indent=2))            # before any result
    slope, train = tmax_slope()

    # ---------------- A. grid
    s = pd.read_csv(ROOT / "outputs" / "grid_ercot" / "daily_summer.csv", parse_dates=["DATE"])
    beta, _, _ = ge.fit(ge.design(s, "tmax", ge.CFG["hinge_F"]), s.peak.to_numpy(float))
    b1, b2 = beta[-2], beta[-1]
    yrs = sorted(s.Year.unique())
    base = beta[0] + beta[1 + yrs.index(2018) - 1]                            # 2018 year effect
    wk = np.array([0.0] + list(beta[len(yrs):len(yrs) + 6]))                  # Monday = 0
    draws = s[s.Year.between(*CFG["draw_years"])]

    def annual_peak(g, shift):
        T = g.tmax.to_numpy(float) + shift
        return float((base + wk[g.DATE.dt.dayofweek.to_numpy()] + b1 * T + b2 * np.maximum(T - ge.CFG["hinge_F"], 0)).max())

    normal = np.mean([annual_peak(g, 0.0) for _, g in draws.groupby("Year")])
    cdr = CFG["ercot_cdr_dec2018"]
    rows = []
    for i, Y in enumerate(range(CFG["forecast_years"][0], CFG["forecast_years"][1] + 1)):
        warm = np.array([annual_peak(g, slope * (Y - y)) for y, g in draws.groupby("Year")])
        eff, hot = warm.mean() - normal, np.quantile(warm, CFG["hot_quantile"]) - normal
        r = {"year": Y, "warming_effect_MW": eff, "hot_summer_effect_MW": hot}
        if Y in cdr["years"]:
            j = cdr["years"].index(Y)
            pk, firm, cap = cdr["peak_normal_weather_MW"][j], cdr["firm_peak_load_MW"][j], cdr["total_capacity_MW"][j]
            red = pk - firm
            for k, add in (("plan", 0.0), ("forecast", eff), ("hot", hot)):
                r[f"peak_{k}_MW"] = pk + add
                r[f"reserve_margin_{k}"] = (cap - (pk + add - red)) / (pk + add - red)
            r["capacity_MW"] = cap
        rows.append(r)
    grid = pd.DataFrame(rows).set_index("year")
    grid.to_csv(OUT / "grid.csv", float_format="%.4f")

    # ---------------- B. bills
    _, cov = load_train()
    flags = valid_flags(train, cov)
    a = train.assign(cdd_v=train.cdd.where(flags["cdd"]))
    w = json.loads((ROOT / "outputs" / "grid_ercot" / "fits.json").read_text())["zone_weights"]
    sub = pd.read_csv(ROOT / "submission.csv")
    sub = sub[sub.metric == "cdd"].pivot_table(index="year", columns="city_id", values="predicted_value")

    def zone_weighted(get):
        tot = 0.0
        for z, ids in ge.ZONES.items():
            tot += w[z] * np.mean([get(c) for c in ids])
        return tot

    cdd_2015 = zone_weighted(lambda c: a[(a.ID == c) & (a.Year == 2015)].cdd_v.iloc[0])
    cdd_base = zone_weighted(lambda c: a[(a.ID == c) & a.Year.between(1976, 2005)].cdd_v.mean())
    cdd_fc = {Y: zone_weighted(lambda c, Y=Y: sub.loc[Y, c]) for Y in sub.index}
    non_cool = CFG["kwh_total"] - CFG["kwh_cooling"]
    brow = []
    for Y, c in [("1976-2005 climate", cdd_base), ("2015 (RECS year)", cdd_2015)] + list(cdd_fc.items()):
        cool = CFG["kwh_cooling"] * c / cdd_2015
        for case, price in (("central", CFG["price_c_kwh_2018"]), ("scarcity", CFG["price_c_kwh_2018"] + CFG["scarcity_adder_c_kwh"])):
            p = price / 100
            bill = (non_cool + cool) * p
            r = {"year": Y, "price_case": case, "cdd": c, "cooling_kwh": cool, "bill_usd": bill}
            for k in ("1", "4"):
                allow = max(CFG["bar"][k] / p - non_cool, 0.0)
                r[f"share_income_{k}"] = bill / CFG["income"][k]
                r[f"x_bar_{k}"] = bill / CFG["bar"][k]
                r[f"cooling_affordable_share_{k}"] = min(allow / cool, 1.0)
            brow.append(r)
    bills = pd.DataFrame(brow)
    bills.to_csv(OUT / "bills.csv", index=False, float_format="%.4f")

    # ---------------- summary
    g = grid.dropna(subset=["capacity_MW"])
    L = ["# Section 5: the forecast window, ERCOT / Texas", "",
         f"All inputs are dated 2018 or earlier. Weather draws: summers {CFG['draw_years'][0]}-{CFG['draw_years'][1]}, warmed by "
         f"{slope:.4f} F/yr (delta method). Demand model: section 3 (peak +{b1:,.0f} MW per F, {b2:+,.0f} MW per F above 95 F). "
         "Plan figures: ERCOT CDR, December 2018.", "",
         "## A. Grid: peak demand and spare capacity", "",
         "| Summer | ERCOT plan peak (normal weather) | + warming (average summer) | + warming (hot summer, 1 in 10) | Capacity | Reserve margin: plan | with warming | hot summer | Target |",
         "|---|---|---|---|---|---|---|---|---|"]
    for Y, r in g.iterrows():
        L.append(f"| {Y} | {r.peak_plan_MW:,.0f} | {r.peak_forecast_MW:,.0f} (+{r.warming_effect_MW:,.0f}) | {r.peak_hot_MW:,.0f} (+{r.hot_summer_effect_MW:,.0f}) | "
                 f"{r.capacity_MW:,.0f} | {r.reserve_margin_plan:.1%} | {r.reserve_margin_forecast:.1%} | {r.reserve_margin_hot:.1%} | {cdr['target_reserve_margin']:.2%} |")
    L += ["", f"- Summers below the {cdr['target_reserve_margin']:.2%} target: plan {(g.reserve_margin_plan < cdr['target_reserve_margin']).sum()} of {len(g)}, "
          f"with warming {(g.reserve_margin_forecast < cdr['target_reserve_margin']).sum()}, hot summer {(g.reserve_margin_hot < cdr['target_reserve_margin']).sum()}.",
          f"- Summers where a hot summer leaves less than 5% spare: {(g.reserve_margin_hot < 0.05).sum()} of {len(g)}.",
          "", "## B. Bills for a poverty-line household (2018 dollars)", "",
          f"Texas cooling degree days (zone-weighted): 1976-2005 average {cdd_base:,.0f}; 2015 {cdd_2015:,.0f}; forecast 2019-2025 "
          f"{min(cdd_fc.values()):,.0f}-{max(cdd_fc.values()):,.0f} (mean {np.mean(list(cdd_fc.values())):,.0f}).", "",
          "| Weather | Price | Cooling use (kWh) | Bill | Share of income: 1 person | 4 people | x bar: 1 person | 4 people | Cooling the bar pays for: 1 person | 4 people |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in bills.iterrows():
        L.append(f"| {r.year} | {r.price_case} | {r.cooling_kwh:,.0f} | ${r.bill_usd:,.0f} | {r.share_income_1:.1%} | {r.share_income_4:.1%} | "
                 f"{r.x_bar_1:.2f} | {r.x_bar_4:.2f} | {r.cooling_affordable_share_1:.0%} | {r.cooling_affordable_share_4:.0%} |")
    fc = bills[(bills.price_case == "central") & bills.year.apply(lambda v: isinstance(v, (int, np.integer)))]
    L += ["", f"- Forecast years in which a family of four at the poverty line goes over the bar (central price): {(fc.x_bar_4 > 1).sum()} of {len(fc)}.",
          "", "## Limits", "",
          "- ERCOT's plan already includes growth; we change only the weather. Its 'normal weather' definition may differ from our 15 draws.",
          "- The hot-summer case is the 90th percentile of 15 warmed draws, a rough one-in-ten summer.",
          "- Household use is a 2015 Southern average for incomes under $20,000, scaled by cooling degree days; real households differ.",
          "- The scarcity case assumes the 2016-2018 wholesale rise reaches bills in full; most plans are fixed-price, so it arrives with a lag."]
    (OUT / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
