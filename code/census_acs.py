"""Download Census ACS 5-year (2019-2023) housing counts for every US county (policy check, not a forecast input).

Tables: B25024 units in structure, B25034 year structure built, B25003 tenure (owner / renter).
Housing counts do not respond to the weather, so any year is allowed (code/AGENTS.md).

Key: put your free Census API key (https://api.census.gov/data/key_signup.html) in `census_key.txt`
at the repo root, replacing YOUR_KEY. That file is in .gitignore; never commit it.
The environment variable CENSUS_API_KEY, if set, is used instead.

Run from the repo root:
    python code/census_acs.py --test          # one county (Allegheny, PA), checks the key works
    python code/census_acs.py                 # all counties -> outputs/policy_check/acs_county_2023.csv
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
KEY_FILE = ROOT / "census_key.txt"
PLACEHOLDER = "hi"
BASE = "https://api.census.gov/data/2023/acs/acs5"
VARS = ([f"B25024_{i:03d}E" for i in range(1, 12)]     # units in structure: total, 1 det, 1 att, 2, 3-4, 5-9, 10-19, 20-49, 50+, mobile, other
        + [f"B25034_{i:03d}E" for i in range(1, 12)]   # year built: total, 2020+, 2010-19, ..., 1940-49, 1939 or earlier
        + [f"B25003_{i:03d}E" for i in range(1, 4)])   # tenure: total, owner, renter


def api_key():
    key = os.environ.get("CENSUS_API_KEY", "").strip()
    if not key and KEY_FILE.exists():
        key = KEY_FILE.read_text().strip()
    if not key or key == PLACEHOLDER:
        sys.exit(f"No Census API key: replace {PLACEHOLDER} in {KEY_FILE.name} (repo root) with your key, "
                 "or set CENSUS_API_KEY. Get one free at https://api.census.gov/data/key_signup.html")
    return key


def acs(variables, geo_for, geo_in=None):
    """One ACS request. Returns a DataFrame. The key is added as &key=... and never printed."""
    key = api_key()
    params = {"get": "NAME," + ",".join(variables), "for": geo_for}
    if geo_in:
        params["in"] = geo_in
    url = f"{BASE}?{urllib.parse.urlencode(params, safe=':*,')}&key={key}"
    try:
        with urllib.request.urlopen(url, timeout=120) as r:
            body = r.read().decode()
    except urllib.error.HTTPError as e:
        sys.exit(f"Census API error HTTP {e.code} (check the key in {KEY_FILE.name}).")
    if body.lstrip().startswith("<"):
        sys.exit(f"Census API returned a web page instead of data: the key in {KEY_FILE.name} was not accepted.")
    rows = json.loads(body)
    df = pd.DataFrame(rows[1:], columns=rows[0])
    for v in variables:
        df[v] = pd.to_numeric(df[v])
    return df


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="fetch one county only, to check the key")
    ap.add_argument("--out", default=str(ROOT / "outputs" / "policy_check" / "acs_county_2023.csv"))
    a = ap.parse_args(argv)
    if a.test:
        df = acs(VARS[:3], "county:003", "state:42")
        print("Key works. Allegheny County, PA:", df.iloc[0].to_dict())
        return
    df = acs(VARS, "county:*")
    df.insert(0, "county_fips", df["state"] + df["county"])
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"{len(df)} counties -> {out}")


if __name__ == "__main__":
    main()
