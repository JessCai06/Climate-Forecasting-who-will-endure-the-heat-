"""Download NOAA GHCN-Daily rows for the 210 challenge stations, SCORING ONLY.
Post-2018 observations are used only to score a frozen forecast, never as a forecast input
(user-approved 2026-11-07 because the private answer key is not accessible).
Keeps 2018-2021 TMAX/TMIN/PRCP (tenths of degC / tenths of mm) per station in one CSV."""
import io, sys, urllib.request, concurrent.futures as cf
from pathlib import Path
import pandas as pd
from huggingface_hub import hf_hub_download

URL = "https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/{}.csv"
ids = sorted(pd.read_parquet(hf_hub_download("CMU-OSPO/protostar-climate-train-to-2018",
        "annual_indices/train-00000-of-00001.parquet", repo_type="dataset"), columns=["ID"]).ID.unique())

def rng(url, a):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"Range": f"bytes={a}"}), timeout=60).read().decode()

def get(i):
    u = URL.format(i)
    header = rng(u, "0-8000").split("\n")[0]
    tail = 2_500_000
    while True:
        body = rng(u, f"-{tail}")
        body = body[body.index("\n") + 1:]
        df = pd.read_csv(io.StringIO(header + "\n" + body), dtype=str, usecols=lambda c: c in ("DATE", "TMAX", "TMIN", "PRCP"))
        if df.DATE.min() <= "2018-01-01" or tail > 40_000_000:
            break
        tail *= 2
    df = df[(df.DATE >= "2018-01-01") & (df.DATE <= "2021-12-31")]
    for c in ("TMAX", "TMIN", "PRCP"):
        df[c] = pd.to_numeric(df[c], errors="coerce") if c in df else float("nan")
    df.insert(0, "ID", i)
    return df

with cf.ThreadPoolExecutor(8) as ex:
    parts = list(ex.map(get, ids))
out = pd.concat(parts, ignore_index=True)
Path(sys.argv[1]).parent.mkdir(parents=True, exist_ok=True)
out.to_csv(sys.argv[1], index=False)
print(out.shape, out.ID.nunique(), out.DATE.min(), out.DATE.max())
