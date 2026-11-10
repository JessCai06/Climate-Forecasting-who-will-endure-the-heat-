"""Policy essay, section 4: prices as they have been, and how affordable they were. Lead case: Texas, 2002-2018.

What it computes
  1. Texas residential electricity, every year 2002-2018, from the utility filings in EIA-861
     (revenue, sales and customers of every utility and retail provider in Texas):
       price (cents/kWh), use per customer (kWh/yr), average bill ($/yr), and the same in 2018 dollars.
     Delivery-only rows (wires companies in the competitive market) add revenue but not sales or customers,
     which their retail provider already reports (EIA's own convention for state totals).
  2. The affordability bar from essay section 1a, in 2018 dollars, for Texas:
       6% of poverty-line income for home energy x electricity's share of Texas home energy spending
       (85%, EIA RECS 2020 state table) = about 5.1% of income.
  3. Bills a poverty-line household would face in 2018, against that bar:
       - the average Texas residential customer's use
       - the average use of Southern households earning under $20,000 (EIA RECS 2015, table CE4.9: 10,829 kWh,
         of which 2,460 kWh for air conditioning)

Inputs (none responds to 2019-2025 weather; data rule in code/AGENTS.md):
  - EIA-861 annual files 2002-2018 (eia.gov/electricity/data/eia861), cached in data/raw/grid/. No later year
    is downloaded.
  - BLS CPI-U, U.S. city average, all items (series CUUR0000SA0), annual average of monthly values, 2002-2018.
  - Constants with sources, from essay section 1a and RECS (listed in CFG below).

Run from the repo root:   python code/policy_grid_prices.py
Writes outputs/grid_prices/: config.json, texas_residential.csv, summary.md
"""
import json
import re
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "grid"
OUT = ROOT / "outputs" / "grid_prices"
EIA = "https://www.eia.gov/electricity/data/eia861/archive/zip/"
CFG = {
    "years": [2002, 2018], "state": "TX", "dollars": 2018,
    "poverty_guideline_2018": {"1": 12140, "4": 25100},        # HHS 2018, 48 states + DC
    "burden_high": 0.06, "burden_severe": 0.10,                 # APPRISE 2005 / ACEEE
    "tx_electricity_share_of_home_energy": 15.77 / 18.46,      # RECS 2020 state table: $15.77bn of $18.46bn
    "us_electricity_share_of_home_energy": 170.47 / 232.76,    # RECS 2020: $170.47bn of $232.76bn
    "south_low_income_kwh": 10829, "south_low_income_ac_kwh": 2460,   # RECS 2015 CE4.9, South, income < $20,000
    "wsc_all_kwh": 14324, "wsc_all_ac_kwh": 4002,               # RECS 2015 CE4.9, West South Central, all homes
}


def eia_file(y):
    name = f"f861{str(y)[2:]}.zip" if y < 2012 else f"f861{y}.zip"
    p = RAW / f"eia_{name}"
    if not p.exists():
        RAW.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(EIA + name, headers={"User-Agent": "Mozilla/5.0 (research script)"})
        p.write_bytes(urllib.request.urlopen(req, timeout=300).read())
    return p


def texas_residential(y):
    z = zipfile.ZipFile(eia_file(y))
    pat = re.compile(r"(^|/)(file2[^/]*\.xls|sales_ult_cust_\d{4}\.xlsx?)$", re.I)
    name = [n for n in z.namelist() if pat.search(n)][0]
    raw = pd.read_excel(z.open(name), header=None)
    head = raw.head(4).astype(str)
    state_col = next(j for j in range(raw.shape[1]) if head[j].str.strip().str.lower().isin(["state", "state_code"]).any())
    svc_col = next(j for j in range(raw.shape[1]) if head[j].str.lower().str.contains("service").any())
    rev_col = min(j for j in range(raw.shape[1]) if head[j].str.contains(r"(?i)res revenue|thousand|residential_revenue").any())
    body = raw[raw[state_col].astype(str).str.strip() == CFG["state"]]
    num = lambda c: pd.to_numeric(body[c], errors="coerce").fillna(0)
    delivery = body[svc_col].astype(str).str.lower().str.contains("deliver")
    rev, mwh, cust = num(rev_col), num(rev_col + 1), num(rev_col + 2)
    return {"year": y, "revenue_k": rev.sum(), "sales_mwh": mwh[~delivery].sum(), "customers": cust[~delivery].sum(),
            "rows": len(body), "delivery_rows": int(delivery.sum()), "file": name}


def cpi():
    p = RAW / "cpi_u_2002_2018.json"
    if not p.exists():
        vals = {}
        for a, b in ((2002, 2011), (2012, 2018)):        # the keyless API returns at most 10 years per call
            req = urllib.request.Request("https://api.bls.gov/publicAPI/v1/timeseries/data/",
                                         data=json.dumps({"seriesid": ["CUUR0000SA0"], "startyear": str(a), "endyear": str(b)}).encode(),
                                         headers={"Content-Type": "application/json"})
            for r in json.loads(urllib.request.urlopen(req, timeout=60).read())["Results"]["series"][0]["data"]:
                if r["period"] != "M13":
                    vals.setdefault(r["year"], []).append(float(r["value"]))
        p.write_text(json.dumps({y: sum(v) / len(v) for y, v in vals.items() if len(v) == 12}, indent=1))
    return {int(k): v for k, v in json.loads(p.read_text()).items()}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "config.json").write_text(json.dumps(CFG, indent=2))            # before any result
    years = range(CFG["years"][0], CFG["years"][1] + 1)
    tx = pd.DataFrame([texas_residential(y) for y in years]).set_index("year")
    c = cpi()
    tx["cpi"] = [c[y] for y in tx.index]
    to18 = c[2018] / tx.cpi
    tx["price_c_kwh"] = tx.revenue_k * 1e3 / (tx.sales_mwh * 1e3) * 100
    tx["kwh_per_customer"] = tx.sales_mwh * 1e3 / tx.customers
    tx["bill_usd"] = tx.revenue_k * 1e3 / tx.customers
    tx["price_c_kwh_2018usd"] = tx.price_c_kwh * to18
    tx["bill_2018usd"] = tx.bill_usd * to18
    tx.to_csv(OUT / "texas_residential.csv", float_format="%.3f")

    share = CFG["tx_electricity_share_of_home_energy"]
    bar = {k: v * CFG["burden_high"] * share for k, v in CFG["poverty_guideline_2018"].items()}
    severe = {k: v * CFG["burden_severe"] * share for k, v in CFG["poverty_guideline_2018"].items()}
    p18 = tx.loc[2018, "price_c_kwh"] / 100
    cases = {
        "Average Texas residential customer": tx.loc[2018, "kwh_per_customer"],
        "Southern household earning under $20,000 (RECS 2015)": CFG["south_low_income_kwh"],
    }
    ac_low = CFG["south_low_income_ac_kwh"] * p18

    g_price = np.polyfit(tx.index, np.log(tx.price_c_kwh_2018usd), 1)[0]
    L = ["# Section 4: Texas electricity prices and bills, 2002-2018, against the affordability bar", "",
         "Source: EIA-861 utility filings (all Texas residential customers, competitive and regulated areas). "
         "2018 dollars with the BLS CPI-U. Bar: essay section 1a, using electricity's share of Texas home energy "
         f"spending ({share:.0%}, RECS 2020) instead of the national {CFG['us_electricity_share_of_home_energy']:.0%}.", "",
         "## 1. Prices and bills", "",
         "| Year | Price (cents/kWh) | Price, 2018 dollars | Use per customer (kWh/yr) | Average bill ($/yr) | Bill, 2018 dollars |",
         "|---|---|---|---|---|---|"]
    for y, r in tx.iterrows():
        L.append(f"| {y} | {r.price_c_kwh:.2f} | {r.price_c_kwh_2018usd:.2f} | {r.kwh_per_customer:,.0f} | {r.bill_usd:,.0f} | {r.bill_2018usd:,.0f} |")
    pk = tx.price_c_kwh_2018usd.idxmax()
    L += ["",
          f"- Real price trend 2002-2018: {g_price*100:+.1f}% a year. Highest real price: {tx.loc[pk, 'price_c_kwh_2018usd']:.1f} cents in {pk} (natural gas price spike); "
          f"2018: {tx.loc[2018, 'price_c_kwh']:.1f} cents.",
          f"- Average use per customer: {tx.kwh_per_customer.mean():,.0f} kWh a year over 2002-2018 (U.S. average about 10,500; Texas homes are larger users because of cooling and electric heat).",
          "", "## 2. The bar in Texas (2018 dollars)", "",
          "| Household at the 2018 poverty line | Income | Electricity bar (6% x 85%) | Severe (10% x 85%) |", "|---|---|---|---|"]
    for k in ("1", "4"):
        L.append(f"| {k} {'person' if k == '1' else 'people'} | ${CFG['poverty_guideline_2018'][k]:,} | ${bar[k]:,.0f} a year (${bar[k]/12:,.0f} a month) | ${severe[k]:,.0f} a year |")
    L += ["", "## 3. Bills a poverty-line household would face in 2018", "",
          "| Use | kWh a year | Bill at the 2018 Texas price | vs bar, 1 person | vs bar, 4 people | Share of income, 1 person | Share of income, 4 people |",
          "|---|---|---|---|---|---|---|"]
    for name, kwh in cases.items():
        b = kwh * p18
        L.append(f"| {name} | {kwh:,.0f} | ${b:,.0f} | {b/bar['1']:.1f}x | {b/bar['4']:.1f}x | "
                 f"{b/CFG['poverty_guideline_2018']['1']*100:.1f}% | {b/CFG['poverty_guideline_2018']['4']*100:.1f}% |")
    L += ["",
          f"- Air conditioning alone for a Southern household under $20,000 (2,460 kWh): ${ac_low:,.0f} a year, "
          f"{ac_low/bar['1']*100:.0f}% of a single person's whole electricity bar.",
          f"- Texas homes on average use {CFG['wsc_all_ac_kwh']:,} kWh a year on cooling (RECS 2015, West South Central): ${CFG['wsc_all_ac_kwh']*p18:,.0f} at the 2018 price.",
          "", "## Limits", "",
          "- Average price across all plans and utilities; individual plans, and the poorest households' rates, differ.",
          "- Low-income use is a regional figure (South, income under $20,000), not Texas-specific, and is from 2015.",
          "- The bar uses the HHS poverty guideline for the 48 states; Texas costs of living differ."]
    (OUT / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    print("\nrows check:", tx[["rows", "delivery_rows", "file"]].to_string())


if __name__ == "__main__":
    main()
