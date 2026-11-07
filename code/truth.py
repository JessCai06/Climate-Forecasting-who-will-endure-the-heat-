"""Annual 'truth' from NOAA daily obs (scoring only). Mirrors annual_indices definitions."""
import numpy as np, pandas as pd

def annual_from_daily(obs: pd.DataFrame, round_f=False) -> pd.DataFrame:
    d = obs.copy()
    d["year"] = d.DATE.str[:4].astype(int)
    f = lambda v: v / 10 * 9 / 5 + 32
    d["tmax"], d["tmin"] = f(d.TMAX), f(d.TMIN)
    if round_f:
        d["tmax"], d["tmin"] = d.tmax.round(), d.tmin.round()
    d["tmax_r"] = d.tmax.round()  # annual_indices Max Tmax is a whole degree F
    d["tavg"] = (d.tmax + d.tmin) / 2
    d["prcp"] = d.PRCP / 254.0  # tenths of mm -> inches
    d["cddd"] = np.maximum(0, d.tavg - 65)
    g = d.groupby(["ID", "year"])
    out = pd.DataFrame({
        "miss_tmax": 0, "avg_temp": g.tavg.mean(), "tot_prcp": g.prcp.sum(),
        "max_tmax": g.tmax_r.max(), "cdd": g.cddd.sum(),
        "miss_tmax": g.tmax.apply(lambda s: s.isna().sum()),
        "miss_tmin": g.tmin.apply(lambda s: s.isna().sum()),
        "miss_prcp": g.prcp.apply(lambda s: s.isna().sum()),
        "miss_both": g.tavg.apply(lambda s: s.isna().sum()),
        "ndays": g.size(),
    }).reset_index()
    return out
