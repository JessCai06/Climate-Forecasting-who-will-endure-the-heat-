"""Policy essay, section 4 (national): electricity prices and bills by state, 2002-2018, and how affordable they
were for low-income households of different sizes.

What it computes
  1. Residential electricity for every state, 2002-2018, from EIA-861 utility filings: price (cents/kWh), use per
     customer, average bill, all also in 2018 dollars (BLS CPI-U). Delivery-only rows add revenue, not sales or
     customers (EIA's convention for state totals). Same parsing as code/policy_grid_prices.py.
  2. Does heat raise prices? Real residential price vs the state's cooling degree days, 2002-2018, with state and
     year effects (the year effect absorbs national swings such as natural gas prices).
  3. Low-income electricity use by household size, from EIA RECS 2015 microdata (5,686 homes, survey weights, 96
     replicate weights for standard errors), by Census region:
       1 person, income under $20,000   (the 2018 poverty line for 1 is $12,140, so this is up to ~165% of it)
       4 people, income under $40,000   (poverty line for 4 is $25,100: up to ~160% of it)
     Total kWh and cooling kWh. (RECS 2015 has no poverty flag; these brackets are the closest.)
  4. Each state's affordability bar (essay section 1a): 6% of the 2018 poverty line x electricity's share of that
     state's home energy spending (EIA RECS 2020 state table). 48 states + DC (Alaska and Hawaii have their own
     poverty lines and no challenge city in most cases; left out).
  5. A low-income household's 2018 bill in each state: RECS use for its region and size, cooling scaled to the
     state's climate (state cooling degree days / region's, both 2015, the RECS year), at the state's 2018 price.

Inputs: none responds to 2019-2025 weather (code/AGENTS.md). Cooling degree days come from the challenge data.

Run from the repo root:   python code/policy_grid_prices_national.py
Writes outputs/grid_prices_national/: config.json, states.csv, recs_low_income.csv, price_vs_cdd.json, summary.md
"""
import json
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shared import load_train, valid_flags
import policy_grid_prices as gp
import policy_grid_demand as gd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "grid"
OUT = ROOT / "outputs" / "grid_prices_national"
RECS15 = "https://www.eia.gov/consumption/residential/data/2015/csv/recs2015_public_v4.csv"
RECS20 = "https://www.eia.gov/consumption/residential/data/2020/state/pdf/State%20expenditures.pdf"
STATES = {"Alabama": "AL", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO", "Connecticut": "CT",
          "Delaware": "DE", "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA", "Idaho": "ID", "Illinois": "IL",
          "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
          "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT",
          "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
          "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA",
          "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
          "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY"}
CENSUS_REGION = {1: ["CT", "ME", "MA", "NH", "RI", "VT", "NJ", "NY", "PA"],
                 2: ["IL", "IN", "MI", "OH", "WI", "IA", "KS", "MN", "MO", "NE", "ND", "SD"],
                 3: ["DE", "DC", "FL", "GA", "MD", "NC", "SC", "VA", "WV", "AL", "KY", "MS", "TN", "AR", "LA", "OK", "TX"],
                 4: ["AZ", "CO", "ID", "MT", "NV", "NM", "UT", "WY", "CA", "OR", "WA"]}
REGION_NAME = {1: "Northeast", 2: "Midwest", 3: "South", 4: "West"}
CFG = {"years": [2002, 2018], "poverty_2018": {"1": 12140, "4": 25100}, "burden_high": 0.06, "burden_severe": 0.10,
       "recs_groups": {"1": {"NHSLDMEM": 1, "MONEYPY_max": 1, "label": "1 person, income < $20,000"},
                       "4": {"NHSLDMEM": 4, "MONEYPY_max": 2, "label": "4 people, income < $40,000"}},
       "recs_fay_eps": 0.5, "recs_replicates": 96, "census_region": CENSUS_REGION}


def cached(name, url):
    p = RAW / name
    if not p.exists():
        RAW.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research script)"})
        p.write_bytes(urllib.request.urlopen(req, timeout=300).read())
    return p


def states_residential(y):
    z = zipfile.ZipFile(gp.eia_file(y))
    pat = re.compile(r"(^|/)(file2[^/]*\.xls|sales_ult_cust_\d{4}\.xlsx?)$", re.I)
    raw = pd.read_excel(z.open([n for n in z.namelist() if pat.search(n)][0]), header=None)
    head = raw.head(4).astype(str)
    sc = next(j for j in range(raw.shape[1]) if head[j].str.strip().str.lower().isin(["state", "state_code"]).any())
    vc = next(j for j in range(raw.shape[1]) if head[j].str.lower().str.contains("service").any())
    rc = min(j for j in range(raw.shape[1]) if head[j].str.contains(r"(?i)res revenue|thousand|residential_revenue").any())
    b = raw[raw[sc].astype(str).str.strip().isin(STATES.values())].copy()
    b["state"] = b[sc].astype(str).str.strip()
    deliv = b[vc].astype(str).str.lower().str.contains("deliver")
    for k, c in (("rev", rc), ("mwh", rc + 1), ("cust", rc + 2)):
        b[k] = pd.to_numeric(b[c], errors="coerce").fillna(0)
    b.loc[deliv, ["mwh", "cust"]] = 0
    g = b.groupby("state")[["rev", "mwh", "cust"]].sum()
    g["year"] = y
    return g.reset_index()


def recs2020_share():
    import pypdf
    txt = "\n".join(p.extract_text() or "" for p in pypdf.PdfReader(cached("recs2020_state_expenditures.pdf", RECS20)).pages[:2])
    out = {}
    for name, ab in STATES.items():
        m = re.search(rf"^{re.escape(name)}\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+\d+%", txt, re.M)
        if m:
            out[ab] = float(m.group(3)) / float(m.group(2))
    return out


def recs_low_income():
    r = pd.read_csv(cached("recs2015_public_v4.csv", RECS15))
    reps = [f"BRRWT{i}" for i in range(1, CFG["recs_replicates"] + 1)]
    k = 1 / (CFG["recs_replicates"] * (1 - CFG["recs_fay_eps"]) ** 2)
    rows = []
    for size, g in CFG["recs_groups"].items():
        x = r[(r.NHSLDMEM == g["NHSLDMEM"]) & (r.MONEYPY <= g["MONEYPY_max"])]
        for reg, d in x.groupby("REGIONC"):
            rec = {"size": size, "region": reg, "region_name": REGION_NAME[reg], "n": len(d)}
            for col in ("KWH", "KWHCOL"):
                est = np.average(d[col], weights=d.NWEIGHT)
                rep = np.array([np.average(d[col], weights=d[w]) for w in reps])
                rec[col.lower()] = est
                rec[f"{col.lower()}_se"] = float(np.sqrt(k * ((rep - est) ** 2).sum()))
            rec["ac_share"] = np.average(d.AIRCOND == 1, weights=d.NWEIGHT)
            rows.append(rec)
    return pd.DataFrame(rows)


def state_cdd():
    """Household-weighted cooling degree days per state and year (valid years only), from challenge cities."""
    train, cov = load_train()
    flags = valid_flags(train, cov)
    a = train.assign(cdd_v=train.cdd.where(flags["cdd"]))[["ID", "Year", "cdd_v"]].dropna()
    cities = gd.city_region_table()
    a = a.merge(cities[["city_id", "state", "households"]], left_on="ID", right_on="city_id")
    t = a.assign(v=a.cdd_v * a.households).groupby(["state", "Year"]).agg(v=("v", "sum"), w=("households", "sum"))
    return (t.v / t.w).rename("cdd").reset_index(), a


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "config.json").write_text(json.dumps(CFG, indent=2))            # before any result
    years = range(CFG["years"][0], CFG["years"][1] + 1)
    st = pd.concat([states_residential(y) for y in years], ignore_index=True)
    cpi = gp.cpi()
    st["to18"] = st.year.map(lambda y: cpi[2018] / cpi[y])
    st["price_c"] = st.rev / st.mwh * 100
    st["price_c_18"] = st.price_c * st.to18
    st["kwh_cust"] = st.mwh * 1e3 / st.cust
    st["bill_18"] = st.rev * 1e3 / st.cust * st.to18

    # --- 2. does heat raise prices? (state and year effects)
    cdd, city_cdd = state_cdd()
    m = st.merge(cdd, left_on=["state", "year"], right_on=["state", "Year"]).dropna(subset=["cdd", "price_c_18"])
    X = pd.get_dummies(m[["state", "year"]].astype(str), drop_first=True).astype(float)
    X.insert(0, "cdd100", m.cdd / 100)
    X.insert(0, "const", 1.0)
    beta, *_ = np.linalg.lstsq(X.to_numpy(), m.price_c_18.to_numpy(), rcond=None)
    res = m.price_c_18.to_numpy() - X.to_numpy() @ beta
    cov = np.linalg.inv(X.T.to_numpy() @ X.to_numpy()) * (res @ res) / (len(m) - X.shape[1])
    pv = {"cents_per_100_cdd": beta[1], "se": float(np.sqrt(cov[1, 1])), "n_state_years": len(m), "states": int(m.state.nunique()),
          "mean_price_c_18": float(m.price_c_18.mean())}
    yfx = {int(c.split("_")[1]): beta[i] for i, c in enumerate(X.columns) if c.startswith("year_")}
    (OUT / "price_vs_cdd.json").write_text(json.dumps(pv, indent=2, default=float))

    # --- 3. RECS low-income use
    li = recs_low_income()
    li.to_csv(OUT / "recs_low_income.csv", index=False, float_format="%.1f")

    # --- 4, 5. bars and 2018 bills
    share = recs2020_share()
    s18 = st[st.year == 2018].set_index("state")
    s18["elec_share"] = pd.Series(share)
    s18 = s18.drop(index=[s for s in ("AK", "HI") if s in s18.index]).dropna(subset=["elec_share"])
    st2reg = {s: r for r, ss in CENSUS_REGION.items() for s in ss}
    s18["census_region"] = s18.index.map(st2reg)
    c15 = cdd[cdd.Year == 2015].set_index("state").cdd
    reg15 = {r: np.average(c15.reindex(ss).dropna(), weights=None) for r, ss in CENSUS_REGION.items()}
    s18["cdd_2015"] = c15
    for size in ("1", "4"):
        u = li[li["size"] == size].set_index("region")
        s18[f"bar_{size}"] = CFG["poverty_2018"][size] * CFG["burden_high"] * s18.elec_share
        s18[f"kwh_base_{size}"] = s18.census_region.map(u.kwh - u.kwhcol)
        s18[f"kwh_cool_{size}"] = s18.census_region.map(u.kwhcol) * s18.cdd_2015 / s18.census_region.map(reg15)
        s18[f"bill_{size}"] = (s18[f"kwh_base_{size}"] + s18[f"kwh_cool_{size}"]) * s18.price_c / 100
        s18[f"x_bar_{size}"] = s18[f"bill_{size}"] / s18[f"bar_{size}"]
        s18[f"share_income_{size}"] = s18[f"bill_{size}"] / CFG["poverty_2018"][size]
    s18.to_csv(OUT / "states.csv", float_format="%.3f")
    ok = s18.dropna(subset=["bill_1", "bill_4"])

    # national averages over time (customer-weighted)
    nat = st.groupby("year").apply(lambda g: pd.Series({"price_c_18": g.rev.sum() / g.mwh.sum() * 100 * g.to18.iloc[0],
                                                        "kwh_cust": g.mwh.sum() * 1e3 / g.cust.sum(),
                                                        "bill_18": g.rev.sum() * 1e3 / g.cust.sum() * g.to18.iloc[0]}), include_groups=False)
    g_price = np.polyfit(nat.index, np.log(nat.price_c_18), 1)[0]
    L = ["# Section 4 (national): electricity prices, bills and affordability by state, 2002-2018", "",
         "EIA-861 utility filings (every state), 2018 dollars with the BLS CPI-U. Low-income use: EIA RECS 2015 microdata. "
         "Bar: 6% of the 2018 poverty line x each state's electricity share of home energy spending (RECS 2020).", "",
         "## 1. The national picture", "",
         "| Year | Price, 2018 cents/kWh | Use per customer (kWh) | Average bill, 2018 $ |", "|---|---|---|---|"]
    for y, r in nat.iterrows():
        if y in (2002, 2006, 2008, 2010, 2012, 2014, 2016, 2018):
            L.append(f"| {y} | {r.price_c_18:.2f} | {r.kwh_cust:,.0f} | {r.bill_18:,.0f} |")
    L += ["", f"- Real price trend 2002-2018: {g_price*100:+.1f}% a year.",
          "", "## 2. Has heat raised prices? (state and year effects, 2002-2018)", "",
          f"- {pv['cents_per_100_cdd']:+.3f} cents/kWh per 100 extra cooling degree days in a year (se {pv['se']:.3f}); "
          f"{pv['n_state_years']} state-years, {pv['states']} states; mean price {pv['mean_price_c_18']:.1f} cents.",
          "- A hotter year moves *use*, not the *price*: price swings are national (year effects: natural gas, policy).",
          "", "## 3. What low-income households use (RECS 2015)", "",
          "| Household | Region | Homes in sample | kWh a year (se) | of which cooling (se) | Has AC |", "|---|---|---|---|---|---|"]
    for _, r in li.iterrows():
        L.append(f"| {CFG['recs_groups'][r['size']]['label']} | {r.region_name} | {r.n} | {r.kwh:,.0f} ({r.kwh_se:,.0f}) | "
                 f"{r.kwhcol:,.0f} ({r.kwhcol_se:,.0f}) | {r.ac_share:.0%} |")
    L += ["", "## 4. 2018 bills against the bar, low-income households (2015 use, 2018 prices)", "",
          f"- States with data: {len(ok)}. Over the bar: **1 person {int((ok.x_bar_1 > 1).sum())}**, "
          f"**4 people {int((ok.x_bar_4 > 1).sum())}**. Over the severe line (10% x electricity share): 1 person {int((ok.share_income_1 > 0.10 * ok.elec_share).sum())}, "
          f"4 people {int((ok.share_income_4 > 0.10 * ok.elec_share).sum())}.",
          f"- Median state: 1 person pays {ok.share_income_1.median():.1%} of a poverty-line income for electricity "
          f"({ok.x_bar_1.median():.2f}x the bar); 4 people {ok.share_income_4.median():.1%} ({ok.x_bar_4.median():.2f}x).", "",
          "| State | Price 2018 (cents) | Bar 1 / 4 people | Bill 1 person | x bar | Bill 4 people | x bar |", "|---|---|---|---|---|---|---|"]
    for s, r in ok.sort_values("x_bar_4", ascending=False).iterrows():
        L.append(f"| {s} | {r.price_c:.1f} | ${r.bar_1:,.0f} / ${r.bar_4:,.0f} | ${r.bill_1:,.0f} | {r.x_bar_1:.2f} | ${r.bill_4:,.0f} | {r.x_bar_4:.2f} |")
    L += ["", "## Limits", "",
          "- RECS income brackets, not exact poverty status; regional use (4 Census regions), scaled to each state's climate for cooling only.",
          "- State average prices; a household's own plan differs. Alaska and Hawaii are left out.",
          "- States without a challenge city have no cooling degree days and drop out of parts 2, 4."]
    (OUT / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
