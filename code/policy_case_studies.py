"""Policy check, case studies: actual mixed-use building counts for Pittsburgh, New York City and Cook County (Chicago).
Building data does not respond to the weather, so any year is allowed (code/AGENTS.md). Not a forecast input.

Run from the repo root:  python code/policy_case_studies.py   -> outputs/policy_check/case_studies.csv
"""
import json
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs" / "policy_check" / "case_studies.csv"
WPRDC = "https://data.wprdc.org/api/3/action/datastore_search_sql"
WPRDC_RES = "65855e14-549e-4992-b5be-d629afc676fa"          # Allegheny County Property Assessments (API version)
PLUTO = "https://data.cityofnewyork.us/resource/64uk-42ks.json"  # NYC PLUTO
COOK_CHARS = "https://datacatalog.cookcountyil.gov/resource/x54s-btds.json"  # Cook residential improvement characteristics
COOK_UNIV = "https://datacatalog.cookcountyil.gov/resource/pabr-t5kh.json"   # Cook parcel universe (current)


def get_json(url, params):
    with urllib.request.urlopen(f"{url}?{urllib.parse.urlencode(params)}", timeout=120) as r:
        return json.loads(r.read().decode())


def soql(url, select, where):
    return get_json(url, {"$select": select, "$where": where})[0]


def pittsburgh():
    codes = "('RETL/APT''S OVER','OFFICE/APARTMENTS OVER')"
    sql = (f'SELECT count(*) n, count("YEARBLT") n_yearbuilt, '
           f'sum(CASE WHEN "YEARBLT" < 1980 THEN 1 ELSE 0 END) n_pre1980 '
           f'FROM "{WPRDC_RES}" WHERE "USEDESC" IN {codes}')
    r = get_json(WPRDC, {"sql": sql})["result"]["records"][0]
    n, nyb = int(r["n"]), int(r["n_yearbuilt"])
    return {"city_name": "Pittsburgh", "source": "Allegheny County Property Assessments (WPRDC)",
            "mixed_use_definition": "USEDESC in RETL/APT'S OVER, OFFICE/APARTMENTS OVER",
            "n_mixed_use": n, "n_with_year_built": nyb, "share_with_year_built": nyb / n,
            "share_pre1980_of_known": int(r["n_pre1980"] or 0) / nyb if nyb else None,
            "n_res_units": None, "share_below_bps_size": None, "bps_size_threshold_sqft": 50000,
            "share_central_ac_of_known": None,
            "note": "Classed COMMERCIAL; the county records building details mainly for residential parcels, "
                    "so year built and floor area are mostly missing."}


def nyc():
    w = "landuse='04'"
    tot = soql(PLUTO, "count(*) AS n, sum(unitsres) AS units", w)
    tot["nyb"] = soql(PLUTO, "count(*) AS n", w + " AND yearbuilt>0")["n"]
    small = soql(PLUTO, "count(*) AS n", w + " AND bldgarea<25000")
    pre = soql(PLUTO, "count(*) AS n", w + " AND yearbuilt>0 AND yearbuilt<1980")
    n, nyb = int(tot["n"]), int(tot["nyb"])
    return {"city_name": "NewYork", "source": "NYC DCP PLUTO (NYC Open Data 64uk-42ks)",
            "mixed_use_definition": "landuse = 04 (mixed residential and commercial)",
            "n_mixed_use": n, "n_with_year_built": nyb, "share_with_year_built": nyb / n,
            "share_pre1980_of_known": int(pre["n"]) / nyb, "n_res_units": float(tot["units"]),
            "share_below_bps_size": int(small["n"]) / n, "bps_size_threshold_sqft": 25000,
            "share_central_ac_of_known": None,
            "note": "Below 25,000 sq ft building area = outside Local Law 97 (approximation: LL97 uses gross floor area)."}


def cook():
    yr = get_json(COOK_CHARS, {"$select": "max(year) AS y", "$where": "class='212'"})[0]["y"]
    w = f"class='212' AND year='{yr}'"
    tot = soql(COOK_CHARS, "count(*) AS n", w)
    tot["nyb"] = soql(COOK_CHARS, "count(*) AS n", w + " AND char_yrblt IS NOT NULL")["n"]
    pre = soql(COOK_CHARS, "count(*) AS n", w + " AND char_yrblt<1980")
    small = soql(COOK_CHARS, "count(*) AS n", w + " AND char_bldg_sf<50000")
    air = get_json(COOK_CHARS, {"$select": "char_air, count(*) AS n", "$where": w, "$group": "char_air"})
    air = {a.get("char_air"): int(a["n"]) for a in air}
    known_air = sum(v for k, v in air.items() if k)
    univ = int(soql(COOK_UNIV, "count(*) AS n", "class='212'")["n"])
    n, nyb = int(tot["n"]), int(tot["nyb"])
    return {"city_name": "Chicago", "source": f"Cook County Assessor improvement characteristics (x54s-btds, year {yr})",
            "mixed_use_definition": "class 212: mixed-use commercial/residential, 6 units or fewer",
            "n_mixed_use": n, "n_with_year_built": nyb, "share_with_year_built": nyb / n,
            "share_pre1980_of_known": int(pre["n"]) / nyb, "n_res_units": None,
            "share_below_bps_size": int(small["n"]) / n, "bps_size_threshold_sqft": 50000,
            "share_central_ac_of_known": air.get("Central A/C", 0) / known_air if known_air else None,
            "note": f"Cook County (whole county). Parcel universe has {univ} class-212 parcels; counts here are building "
                    f"records (cards). AC field: {air}. Chicago's benchmarking threshold is 50,000 sq ft."}


def main():
    df = pd.DataFrame([pittsburgh(), nyc(), cook()])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(df.drop(columns=["note", "source", "mixed_use_definition"]).to_string(index=False))
    for r in df.itertuples():
        print(f"- {r.city_name}: {r.note}")


if __name__ == "__main__":
    main()
