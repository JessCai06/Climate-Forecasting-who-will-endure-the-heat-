# Data card: `data/`

The challenge dataset is downloaded at run time. Experiment 6 adds one curated source, stored in `data/neighbors/`.

## Not uploaded (download instead)

| Source | Exact version | How to download | Why not uploaded |
|---|---|---|---|
| [CMU-OSPO/protostar-climate-train-to-2018](https://huggingface.co/datasets/CMU-OSPO/protostar-climate-train-to-2018): `annual_indices`, `coverage_and_stations` (CC0-1.0), years up to 2018 | the dataset revision is recorded in `outputs/exp03/run_log.json` (`dataset_revision`) | `code/shared.py` `load_train()` (`huggingface_hub.hf_hub_download`, `repo_type="dataset"`) | Public and reproducible. `daily` and `city_info` are not used. |

## Uploaded: `data/neighbors/` (Experiment 6)

| File | Content | Source | License |
|---|---|---|---|
| `stations.csv` | For each challenge city (`city_id`), up to 8 nearby GHCN-Daily stations (`sid`), with distance (`km`) and name | Chosen by `code/exp06_fetch_neighbors.py` from `ghcnd-stations.txt` and `ghcnd-inventory.txt` (NOAA NCEI, GHCN-Daily v3.3 metadata, downloaded 2026-11-08) | U.S. Government work, no restrictions (NOAA NCEI) |
| `annual.csv` | One row per station and year, 1969-2018: `avg_temp`, `tot_prcp`, `max_tmax`, `cdd` and missing-day counts | Daily TMAX/TMIN/PRCP from the NOAA NCEI Access Data Service (`dataset=daily-summaries`, `endDate=2018-12-31`), downloaded 2026-11-08 | same |

- **Selection rule:** U.S. stations within 100 km of the city and more than 2 km away, reporting TMAX and TMIN from 1969 or earlier through 2018; the 8 closest. 1,407 stations, 1,621 city-station pairs; every city has at least one.
- **Cutoff:** every request ends at 2018-12-31 on the server side; the script stops if any row is later, and `exp06_neighbors.py` checks again on load.
- **Preparation:** °C and mm converted to °F and inches; yearly values follow the challenge definitions (mean of (Tmax+Tmin)/2, precipitation sum, highest Tmax rounded to a whole degree, cdd base 65 °F). Missing days = days in the year minus days with a value.
- **Raw daily files** are cached in `data/raw/` and not uploaded (about 0.9 GB); rerun `python code/exp06_fetch_neighbors.py` to rebuild them.
- **Citation:** Menne, M.J., et al. (2012). An overview of the Global Historical Climatology Network-Daily database. *J. Atmos. Oceanic Technol.*, 29, 897-910. https://doi.org/10.1175/JTECH-D-11-00103.1

## How the files fit together
- **Join key:** `ID` (= `city_id` in `submission.csv`) and `Year`.
- **Units:** °F, inches, °F-days, as in the source.
- **Preparation:** `+inf/-inf` in `Max Tmax` (years with every day missing) become NaN. A city-year is valid for a metric if it misses at most 10 days of what the metric needs (`Miss Prcp`; `Miss Tmax`; the larger of `Miss Tmax` and `Miss Tmin`; for `cdd`, days in the year minus `Days Both`). Invalid years are never used.
- **Known limitations:** station records start in different years; some cities have fewer than 10 valid years in 1989-2018 and use a fallback (plain average of the valid years they have).

## Data rule check
- [x] Every forecast input is weather data up to 2018-12-31 (enforced by `shared.assert_cutoff` for the challenge data and by the download end date plus load-time checks for `data/neighbors/`).
- [x] No 2019-2025 data is read by the forecasting code. Post-2018 NOAA observations were used only to score the frozen forecast afterwards (see README); they are not stored in the dataset.
