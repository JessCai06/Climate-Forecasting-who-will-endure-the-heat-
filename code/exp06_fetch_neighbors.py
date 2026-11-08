"""Experiment 6, step 1: daily weather from nearby NOAA GHCN-Daily stations, CAPPED AT 2018-12-31.

For each of the 210 challenge cities, pick up to N_MAX nearby stations that:
  - are U.S. GHCN-Daily stations within RADIUS_KM of the city (and more than 2 km away, so the city's own
    site is not counted twice), and
  - report TMAX and TMIN from FIRST_YEAR or earlier through at least 2018 (from ghcnd-inventory.txt).
Then download their daily TMAX/TMIN/PRCP for FIRST_YEAR..2018 from NOAA's Access Data Service with
endDate=2018-12-31 (the server returns nothing later), and turn them into yearly values with the challenge's
definitions (see annual_indices()).

Run from the repo root:   python code/exp06_fetch_neighbors.py
Writes data/neighbors/stations.csv (chosen stations and distances) and data/neighbors/annual.csv
(one row per station and year, 1969-2018). Raw daily files are cached in data/raw/daily/ (not committed).

Data rule: every download ends at 2018-12-31, and annual.csv is checked for that before it is written.
"""
import calendar
import concurrent.futures as cf
import io
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shared import CUTOFF_YEAR, load_train

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "neighbors"
META = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/{}"
API = ("https://www.ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries&stations={}"
       "&startDate={}-01-01&endDate={}-12-31&dataTypes=TMAX,TMIN,PRCP&format=csv&units=metric")
RADIUS_KM, MIN_KM, N_MAX = 100, 2, 8
FIRST_YEAR = 1969             # the earliest held-back window (origin 1998) starts in 1969


def haversine(lat1, lon1, lat2, lon2):
    p1, p2, dl = np.radians(lat1), np.radians(lat2), np.radians(lon2 - lon1)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def metadata(name):
    path = RAW / name
    if not path.exists():
        RAW.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(META.format(name), path)
    return path


def choose_stations(cities):
    st = pd.read_fwf(metadata("ghcnd-stations.txt"), colspecs=[(0, 11), (12, 20), (21, 30), (41, 71)],
                     names=["sid", "lat", "lon", "name"])
    inv = pd.read_fwf(metadata("ghcnd-inventory.txt"), colspecs=[(0, 11), (31, 35), (36, 40), (41, 45)],
                      names=["sid", "el", "first", "last"])
    inv = inv[inv.el.isin(["TMAX", "TMIN"])]
    span = inv.groupby("sid").agg(first=("first", "max"), last=("last", "min"), n=("el", "size"))
    ok = span[(span.n == 2) & (span["first"] <= FIRST_YEAR) & (span["last"] >= CUTOFF_YEAR)].index
    st = st[st.sid.str.startswith("US") & st.sid.isin(ok)]
    rows = []
    for c in cities.itertuples():
        d = haversine(c.Lat, c.Lon, st.lat.values, st.lon.values)
        pick = st.assign(km=d)[(d <= RADIUS_KM) & (d > MIN_KM) & (st.sid != c.ID)].nsmallest(N_MAX, "km")
        rows += [{"city_id": c.ID, "sid": r.sid, "km": round(r.km, 2), "name": r.name} for r in pick.itertuples()]
    return pd.DataFrame(rows)


def fetch(sid):
    cache = RAW / "daily" / f"{sid}.csv"
    if cache.exists():
        return pd.read_csv(cache, dtype={"STATION": str, "DATE": str})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(API.format(sid, FIRST_YEAR, CUTOFF_YEAR), timeout=120) as r:
                txt = r.read().decode()
            break
        except Exception:
            time.sleep(5 * (attempt + 1))
    else:
        raise RuntimeError(f"download failed: {sid}")
    df = pd.read_csv(io.StringIO(txt), dtype={"STATION": str, "DATE": str})
    if len(df) and df.DATE.max() > f"{CUTOFF_YEAR}-12-31":
        raise ValueError(f"{sid}: data after {CUTOFF_YEAR}")
    cache.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(cache, index=False)
    return df


def annual_indices(df):
    """Yearly values with the challenge's definitions (as in annual_indices / code/truth.py), metric units in.
    Missing-day counts are days in the year minus days with a value, so absent rows count as missing."""
    d = df.copy()
    for c in ("TMAX", "TMIN", "PRCP"):
        d[c] = pd.to_numeric(d[c], errors="coerce") if c in d else np.nan
    # drop physically impossible readings (bad or flagged values): U.S. records are -62 C .. 57 C,
    # Tmin above Tmax is an error, and no U.S. day has exceeded ~1000 mm of rain
    d.loc[~d.TMAX.between(-62, 57), "TMAX"] = np.nan
    d.loc[~d.TMIN.between(-62, 57), "TMIN"] = np.nan
    bad = d.TMIN > d.TMAX
    d.loc[bad, ["TMAX", "TMIN"]] = np.nan
    d.loc[~d.PRCP.between(0, 1000), "PRCP"] = np.nan
    d["year"] = d.DATE.str[:4].astype(int)
    d["tmax"], d["tmin"] = d.TMAX * 9 / 5 + 32, d.TMIN * 9 / 5 + 32
    d["tavg"] = (d.tmax + d.tmin) / 2
    d["prcp"] = d.PRCP / 25.4
    d["cddd"] = np.maximum(0, d.tavg - 65)
    g = d.groupby(["STATION", "year"])
    out = pd.DataFrame({"avg_temp": g.tavg.mean(), "tot_prcp": g.prcp.sum(min_count=1),
                        "max_tmax": g.tmax.max().round(), "cdd": g.cddd.sum(min_count=1),
                        "n_tmax": g.tmax.count(), "n_tmin": g.tmin.count(), "n_prcp": g.prcp.count(),
                        "n_both": g.tavg.count()}).reset_index()
    days = out.year.map(lambda y: 366 if calendar.isleap(y) else 365)
    for k in ("tmax", "tmin", "prcp", "both"):
        out[f"miss_{k}"] = days - out.pop(f"n_{k}")
    return out.rename(columns={"STATION": "sid"})


def main():
    train_df, _ = load_train()
    cities = train_df.groupby("ID")[["Lat", "Lon"]].first().reset_index()
    nb = choose_stations(cities)
    OUT.mkdir(parents=True, exist_ok=True)
    nb.to_csv(OUT / "stations.csv", index=False)
    sids = sorted(nb.sid.unique())
    print(f"{len(nb)} city-station pairs, {len(sids)} stations, "
          f"{nb.groupby('city_id').size().reindex(cities.ID, fill_value=0).eq(0).sum()} cities with none")
    parts = []
    with cf.ThreadPoolExecutor(4) as ex:
        for i, df in enumerate(ex.map(fetch, sids), 1):
            if len(df):
                parts.append(annual_indices(df))
            if i % 50 == 0:
                print(f"  {i}/{len(sids)}", flush=True)
    ann = pd.concat(parts, ignore_index=True)
    assert ann.year.max() <= CUTOFF_YEAR, "post-2018 data found"
    ann.to_csv(OUT / "annual.csv", index=False, float_format="%.4f")
    print("wrote", OUT, ann.shape, ann.year.min(), ann.year.max())


if __name__ == "__main__":
    main()
