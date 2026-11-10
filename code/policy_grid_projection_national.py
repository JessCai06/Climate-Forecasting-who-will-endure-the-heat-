"""Policy essay, section 5 (national): the forecast window 2019-2025. Does planning on past weather leave grids and
low-income households exposed as heat rises?

Everything is made with data dated 2018 or earlier (code/AGENTS.md). No 2019-2025 observation is read.

A. Grid: spare capacity by NERC assessment area (U.S. areas of NERC's December 2018 Long-Term Reliability Assessment)
   - Plan: NERC's Anticipated Reserve Margin and Reference Margin Level for 2019-2025 (Tables 3.1-3.2), parsed from
     the report. Margins rest on each area's 50/50 peak forecast (a midpoint; NERC: weather can push demand above it).
   - Weather: each area's challenge cities (household-weighted daily highs, summers 2004-2018). For year Y, the
     summer of year y is warmed by the shared Tmax slope x (Y - y) (delta method, as in the submitted forecast).
     The peak day's high in each warmed summer, minus the average peak-day high of the unwarmed summers, gives
       warming (average summer)  = mean over the 15 warmed summers
       hot summer (about 1 in 10) = 90th percentile of the warmed summers
     times the area's sensitivity (% of peak per F, section 3, EIA-930 2015-2018) = % added to the 50/50 peak.
   - Margin with weather = (1 + plan margin) / (1 + added %) - 1, against the Reference Margin Level.
   - Breakdown for 2025: change in the plan's own margin 2019 -> 2025 (growth, retirements, new plants), warming,
     and a hot summer, all in percentage points of margin.
   - Hot nights: the overnight floor rises by the area's night sensitivity x the shared Tmin slope x (Y - y).
   Assumption to state: the 50/50 forecasts are built from past weather and do not already include warming.

B. Bills for low-income households by state (2018 dollars), 2019-2025
   - Use: section 4 (RECS 2015, by Census region and household size: 1 person < $20k, 4 people < $40k); cooling
     use scaled by the state's forecast cooling degree days (submission.csv, household-weighted cities) relative to
     its region's 2015 value, exactly as section 4 scaled 2015.
   - Price: the state's 2018 price. Scenario (labelled as such): +1.10 cents/kWh in states whose NERC area falls
     below its Reference Margin Level in a hot summer that year, the size of ERCOT's 2016-2018 wholesale rise as its
     reserves shrank (Potomac Economics). Section 4 found no link from hot years to price over 2002-2018, so this is
     a risk case, not a forecast.
   - Bar: section 4 (6% of the 2018 poverty line x the state's electricity share of home energy).

C. Livability by state: share of homes without AC (Census LACE 2023) and forecast cooling-required days / hot nights
   (section 2), household-weighted; and the share of income a low-income household must spend to keep cooling on.

Run from the repo root (after policy_grid_heat_days.py, policy_grid_demand.py, policy_grid_prices_national.py):
    python code/policy_grid_projection_national.py
Writes outputs/grid_projection_national/: config.json, areas.csv, states.csv, summary.md
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shared import load_train
import exp02_line_forest as e2
import exp05_levels_slopes as e5
import policy_grid_demand as gd
import policy_grid_prices_national as gpn

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "grid"
OUT = ROOT / "outputs" / "grid_projection_national"
LTRA = "https://www.nerc.com/pa/RAPA/ra/Reliability%20Assessments%20DL/NERC_LTRA_2018_12202018.pdf"
R = gd.REGION_STATES
AREAS = {   # NERC assessment area: (EIA region for sensitivity, states for weather and bills)
    "FRCC": ("FLA", R["FLA"]), "MISO": ("MIDW", R["MIDW"]), "NPCC-NewEngland": ("NE", R["NE"]),
    "NPCC-NewYork": ("NY", R["NY"]), "PJM": ("MIDA", R["MIDA"]), "SERC-E": ("CAR", R["CAR"]), "SERC-N": ("TEN", R["TEN"]),
    "SERC-SE": ("SE", R["SE"]), "SPP": ("CENT", R["CENT"]), "TRE-ERCOT": ("TEX", R["TEX"]), "WECC-CAMX": ("CAL", R["CAL"]),
    "WECC-NWPP-US": ("NW", ["WA", "OR", "ID", "MT", "UT", "NV"]), "WECC-RMRG": ("NW", ["CO", "WY"]),
    "WECC-SRSG": ("SW", R["SW"])}
CITY_AREA = {"USW00023044": "WECC-SRSG", "USW00023047": "SPP"}        # El Paso, Amarillo
CFG = {"years": [2019, 2025], "draw_years": [2004, 2018], "hot_quantile": 0.9, "areas": AREAS, "city_area": CITY_AREA,
       "scarcity_adder_c_kwh": (35.63 - 24.62) / 10, "ltra": "NERC 2018 LTRA, Tables 3.1-3.2", "emergency_margin": 0.05}


def ltra_margins():
    import pypdf
    p = gpn.cached("nerc_ltra_2018.pdf", LTRA)
    txt = "\n".join((pg.extract_text() or "") for pg in pypdf.PdfReader(p).pages if "Planning Reserve Margins" in (pg.extract_text() or ""))
    rows = []
    for area in AREAS:
        key = area.replace("NPCC-New", "NPCC-New").replace("-", r"\s*-\s*")
        m = re.search(rf"^{key}\s*\nAnticipated ([\d. ]+)\nProspective [\d. ]+\nReference Margin Level ([\d. ]+)", txt, re.M)
        if not m:
            raise ValueError(f"LTRA table: {area} not found")
        ant, ref = [float(v) for v in m.group(1).split()], [float(v) for v in m.group(2).split()]
        for i, y in enumerate(range(2019, 2029)):
            rows.append({"area": area, "year": y, "anticipated": ant[i] / 100, "reference": ref[i] / 100})
    return pd.DataFrame(rows)


def slopes():
    train, _ = load_train()
    d = train[train.Year <= 2018]
    out = {}
    for col, avg, miss in (("tmax", "Avg Tmax", "Miss Tmax"), ("tmin", "Avg Tmin", "Miss Tmin")):
        ser = e2._window_series(d, d[avg].where(d[miss] <= 10), 2018)
        out[col] = e5._shared_slope(ser, sorted(c for c, s in ser.items() if len(s) >= e2.MIN_VALID))
    return out


def area_cities():
    c = gd.city_region_table()
    st2area = {s: a for a, (_, ss) in AREAS.items() for s in ss}
    c["area"] = c.city_id.map(CITY_AREA).fillna(c.state.map(st2area))
    return c.dropna(subset=["area"])


def wmean(df, col, by):
    x = df.dropna(subset=[col])
    t = x.assign(v=x[col] * x.households).groupby(by).agg(v=("v", "sum"), w=("households", "sum"))
    return t.v / t.w


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "config.json").write_text(json.dumps(CFG, indent=2))            # before any result
    sl = slopes()
    sens = pd.read_csv(ROOT / "outputs" / "grid_national" / "sensitivity.csv").set_index("Region")
    plan = ltra_margins()
    cities = area_cities()

    # ---------------- A. grid by area
    W = gd.region_weather(cities.assign(Region=cities.area), tuple(CFG["draw_years"]))
    W = W[W.Date.dt.month.isin([6, 7, 8, 9])]
    peak_T = W.assign(y=W.Date.dt.year).groupby(["Region", "y"]).tmax.max()
    rows = []
    for area, (reg, _) in AREAS.items():
        pT = peak_T.loc[area]
        normal = pT.mean()
        for Y in range(CFG["years"][0], CFG["years"][1] + 1):
            warm = pT.to_numpy() + sl["tmax"] * (Y - pT.index.to_numpy())
            dT_avg, dT_hot = warm.mean() - normal, np.quantile(warm, CFG["hot_quantile"]) - normal
            pct = sens.loc[reg, "pct_per_F_day"] / 100
            p = plan[(plan.area == area) & (plan.year == Y)].iloc[0]
            add_avg, add_hot = pct * dT_avg, pct * dT_hot
            rows.append({"area": area, "region": reg, "year": Y, "plan_margin": p.anticipated, "reference": p.reference,
                         "dT_warming_F": dT_avg, "dT_hot_F": dT_hot, "added_pct_warming": add_avg, "added_pct_hot": add_hot,
                         "margin_warming": (1 + p.anticipated) / (1 + add_avg) - 1, "margin_hot": (1 + p.anticipated) / (1 + add_hot) - 1,
                         "night_floor_pct": sens.loc[reg, "pct_per_F_night"] / 100 * sl["tmin"] * (Y - pT.index.to_numpy()).mean(),
                         "pct_per_F": pct})
    A = pd.DataFrame(rows)
    # The Reference Margin Level is sized to cover weather swings around the 50/50 forecast (and outages), so the
    # 50/50 margin is compared with it; a hot summer is compared with running short (below 0) or emergency
    # territory (below 5% spare: ERCOT's August 2011 alerts came with reserves of a few percent).
    A["below_ref_plan"] = A.plan_margin < A.reference
    A["below_ref_warming"] = A.margin_warming < A.reference
    A["hot_below_5"] = A.margin_hot < CFG["emergency_margin"]
    A["hot_below_0"] = A.margin_hot < 0
    A.to_csv(OUT / "areas.csv", index=False, float_format="%.4f")

    # ---------------- B. bills by state
    st = pd.read_csv(ROOT / "outputs" / "grid_prices_national" / "states.csv").set_index("state")
    li = pd.read_csv(ROOT / "outputs" / "grid_prices_national" / "recs_low_income.csv", dtype={"size": str})
    cdd, _ = gpn.state_cdd()
    c15 = cdd[cdd.Year == 2015].set_index("state").cdd
    reg15 = {r: c15.reindex(ss).dropna().mean() for r, ss in gpn.CENSUS_REGION.items()}
    base = cdd[cdd.Year.between(1976, 2005)].groupby("state").cdd.mean()
    sub = pd.read_csv(ROOT / "submission.csv")
    sub = sub[sub.metric == "cdd"].merge(cities[["city_id", "state", "households"]], on="city_id")
    fc = (sub.assign(v=sub.predicted_value * sub.households).groupby(["state", "year"]).agg(v=("v", "sum"), w=("households", "sum")))
    fc = (fc.v / fc.w).rename("cdd").reset_index()
    st2area = {s: a for a, (_, ss) in AREAS.items() for s in ss}
    hot_area = A.set_index(["area", "year"]).hot_below_5
    brow = []
    for s, r in st.dropna(subset=["bill_1", "bill_4"]).iterrows():
        region = int(r.census_region)
        cases = [("1976-2005", base.get(s, np.nan))] + [(int(y), v) for y, v in fc[fc.state == s][["year", "cdd"]].itertuples(index=False)]
        for label, c in cases:
            if pd.isna(c):
                continue
            rec = {"state": s, "area": st2area.get(s), "weather": label, "cdd": c}
            scarce = isinstance(label, int) and st2area.get(s) is not None and bool(hot_area.get((st2area[s], label), False))
            for size in ("1", "4"):
                u = li[(li["size"] == size) & (li.region == region)].iloc[0]
                cool = u.kwhcol * c / reg15[region]
                kwh = u.kwh - u.kwhcol + cool
                for case, price in (("central", r.price_c), ("scarcity", r.price_c + (CFG["scarcity_adder_c_kwh"] if scarce else 0))):
                    bill = kwh * price / 100
                    rec[f"bill_{size}_{case}"] = bill
                    rec[f"x_bar_{size}_{case}"] = bill / r[f"bar_{size}"]
                rec[f"cooling_cost_share_{size}"] = cool * r.price_c / 100 / gpn.CFG["poverty_2018"][size]
            rec["scarcity_applies"] = scarce
            brow.append(rec)
    B = pd.DataFrame(brow)

    # ---------------- C. livability by state
    hd = pd.read_csv(ROOT / "outputs" / "grid_heat_days" / "city_heat_days.csv").merge(cities[["city_id", "households", "no_ac_pct"]], on="city_id")
    liv = pd.DataFrame({k: wmean(hd, k, "state") for k in ("hot_days_base", "hot_days_fc", "hot_nights_base", "hot_nights_fc", "no_ac_pct")})
    fcm = B[B.weather.apply(lambda v: isinstance(v, int))].groupby("state").mean(numeric_only=True)
    b0 = B[B.weather == "1976-2005"].set_index("state")
    S = liv.join(fcm[["x_bar_1_central", "x_bar_4_central", "x_bar_1_scarcity", "x_bar_4_scarcity", "cooling_cost_share_1", "cooling_cost_share_4", "bill_1_central", "bill_4_central"]], how="inner")
    S = S.join(b0[["x_bar_1_central", "x_bar_4_central", "bill_1_central", "bill_4_central"]].add_suffix("_1976_2005"))
    S["added_bill_1"] = S.bill_1_central - S.bill_1_central_1976_2005
    S["added_bill_4"] = S.bill_4_central - S.bill_4_central_1976_2005
    S["area"] = S.index.map(st2area)
    S.to_csv(OUT / "states.csv", float_format="%.3f")

    # ---------------- summary
    a25 = A[A.year == 2025].set_index("area")
    a19 = A[A.year == 2019].set_index("area")
    L = ["# Section 5 (national): the forecast window, 2019-2025", "",
         f"Inputs dated 2018 or earlier. Plan: NERC 2018 LTRA (Anticipated Reserve Margins, 50/50 peak). Warming: summers "
         f"{CFG['draw_years'][0]}-{CFG['draw_years'][1]} warmed by {sl['tmax']:.4f} F/yr (highs) / {sl['tmin']:.4f} F/yr (lows). "
         "Sensitivity: section 3 (EIA-930). Bills: section 4 (RECS 2015 use by household size, 2018 prices).", "",
         "## A. Spare capacity by NERC area", "",
         "| Area | Sensitivity (% per F) | Plan margin 2019 -> 2025 | Reference | 2025 with warming | Years below reference: plan / with warming | 2025 hot summer | Hot-summer years under 5% spare (of 7) | Overnight floor 2025 |",
         "|---|---|---|---|---|---|---|---|---|"]
    for area in a25.sort_values("margin_hot").index:
        r, r0 = a25.loc[area], a19.loc[area]
        g = A[A.area == area]
        L.append(f"| {area} | {r.pct_per_F*100:.1f}% | {r0.plan_margin:.1%} -> {r.plan_margin:.1%} | {r.reference:.1%} | {r.margin_warming:.1%} | "
                 f"{int(g.below_ref_plan.sum())} / {int(g.below_ref_warming.sum())} | {r.margin_hot:.1%} | {int(g.hot_below_5.sum())} | +{r.night_floor_pct:.1%} |")
    L += ["", "Breakdown of the change in margin to 2025 (percentage points; median area): "
          f"plan's own change 2019 -> 2025 {np.median((a25.plan_margin - a19.plan_margin) * 100):+.1f}; "
          f"warming {np.median((a25.margin_warming - a25.plan_margin) * 100):+.1f}; "
          f"hot summer {np.median((a25.margin_hot - a25.plan_margin) * 100):+.1f}.",
          f"- Area-years (7 years x {len(AREAS)} areas = {len(A)}) below the reference margin: plan {int(A.below_ref_plan.sum())}, "
          f"with warming {int(A.below_ref_warming.sum())}. Hot summer with under 5% spare: {int(A.hot_below_5.sum())}; short of capacity (below 0): {int(A.hot_below_0.sum())}.",
          f"- Warming as a share of the plan's cushion above the reference level, 2025 (median area): "
          f"{np.median((a25.plan_margin - a25.margin_warming) / (a25.plan_margin - a25.reference).clip(lower=0.005)):.0%}.",
          f"- Average extra peak-day heat from warming: {A.dT_warming_F.min():.2f} to {A.dT_warming_F.max():.2f} F; "
          f"a hot summer: {A.dT_hot_F.median():.1f} F (median area-year).",
          "", "## B. Bills for low-income households by state (2018 dollars)", "",
          f"- States: {len(S)}. Over the bar, 1976-2005 climate: 1 person {int((S.x_bar_1_central_1976_2005 > 1).sum())}, 4 people {int((S.x_bar_4_central_1976_2005 > 1).sum())}. "
          f"Forecast 2019-2025 (average): 1 person {int((S.x_bar_1_central > 1).sum())}, 4 people {int((S.x_bar_4_central > 1).sum())}. "
          f"Scarcity scenario: 4 people {int((S.x_bar_4_scarcity > 1).sum())}.",
          f"- Added bill from the forecast heat vs 1976-2005 (median state): 1 person ${S.added_bill_1.median():,.0f}, 4 people ${S.added_bill_4.median():,.0f} a year "
          f"(largest: {S.added_bill_4.idxmax()} ${S.added_bill_4.max():,.0f}).",
          f"- Share of a poverty-line income needed just to keep cooling on (forecast, median state): 1 person {S.cooling_cost_share_1.median():.1%}, "
          f"4 people {S.cooling_cost_share_4.median():.1%}; highest {S.cooling_cost_share_1.idxmax()} {S.cooling_cost_share_1.max():.1%} (1 person).",
          "", "## C. Livability by state (forecast 2019-2025)", "",
          "| State | Area | No AC % | Cooling-required days (base -> forecast) | Hot nights | 1 person x bar | 4 people x bar | Cooling cost, % of income (1 person) |",
          "|---|---|---|---|---|---|---|---|"]
    for s, r in S.sort_values("hot_days_fc", ascending=False).iterrows():
        L.append(f"| {s} | {r.area} | {r.no_ac_pct:.1f} | {r.hot_days_base:.0f} -> {r.hot_days_fc:.0f} | {r.hot_nights_base:.0f} -> {r.hot_nights_fc:.0f} | "
                 f"{r.x_bar_1_central:.2f} | {r.x_bar_4_central:.2f} | {r.cooling_cost_share_1:.1%} |")
    L += ["", "## Limits", "",
          "- Assumes the 50/50 peak forecasts do not already include warming; if an area's forecast does, its warming line overstates.",
          "- Linear demand response; peak-day temperature stands in for the peak hour. Load-weighted cities by state, approximate at area borders.",
          "- The hot summer is the 90th percentile of 15 warmed summers; the scarcity price is a scenario (section 4 found no link from hot years to price).",
          "- Household use: RECS 2015 by Census region and size, cooling scaled by state cooling degree days."]
    (OUT / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
