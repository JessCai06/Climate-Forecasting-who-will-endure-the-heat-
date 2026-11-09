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
- **Raw daily files** are cached in `data/raw/` and not uploaded (about 0.9 GB); rerun `python code/exp06_fetch_neighbors.py` to rebuild them. Experiment 9 (`code/exp09_daily_gapfill.py`) reads these raw daily files to fill missing days at each city's station; the city's own daily values come from the challenge dataset's `daily` table (up to 2018). Experiment 5B reads only that `daily` table.
- **Citation:** Menne, M.J., et al. (2012). An overview of the Global Historical Climatology Network-Daily database. *J. Atmos. Oceanic Technol.*, 29, 897-910. https://doi.org/10.1175/JTECH-D-11-00103.1

## How the files fit together
- **Join key:** `ID` (= `city_id` in `submission.csv`) and `Year`.
- **Units:** °F, inches, °F-days, as in the source.
- **Preparation:** `+inf/-inf` in `Max Tmax` (years with every day missing) become NaN. A city-year is valid for a metric if it misses at most 10 days of what the metric needs (`Miss Prcp`; `Miss Tmax`; the larger of `Miss Tmax` and `Miss Tmin`; for `cdd`, days in the year minus `Days Both`). Invalid years are never used.
- **Known limitations:** station records start in different years; some cities have fewer than 10 valid years in 1989-2018 and use a fallback (plain average of the valid years they have).

## Data rule check
- [x] Every forecast input is weather data up to 2018-12-31 (enforced by `shared.assert_cutoff` for the challenge data and by the download end date plus load-time checks for `data/neighbors/`).
- [x] No 2019-2025 data is read by the forecasting code. Post-2018 NOAA observations were used only to score the frozen forecast afterwards (see README); they are not stored in the dataset.

## Policy heuristic check (analysis only, not a forecast input)

Used only by `code/policy_check.py`, `code/policy_case_studies.py` and `code/census_acs.py`; outputs in `outputs/policy_check/`. The forecast code never reads any of it.

| Source | What | How to get it |
|---|---|---|
| NOAA GHCN-Daily, 2019-2025, 210 stations | Observed weather, a **stand-in** for the forecast (team-approved 2026-11-08; analysis only) | `python code/fetch_truth.py obs_2021_2025.csv 2021-01-01 2025-12-31` (2019-2020 from `obs_2018_2021.csv`) |
| Census ACS 5-year 2019-2023, B25024 / B25034 / B25003, all counties | Building size, year built, tenure (not weather-driven) | `python code/census_acs.py` (needs a free key in `census_key.txt`, which git ignores) |
| FCC Area API | Station latitude/longitude to county | Called by `code/policy_check.py`, cached in `station_county.csv` |
| Allegheny County Property Assessments (WPRDC), NYC PLUTO, Cook County Assessor improvement characteristics | Actual mixed-use building counts for Pittsburgh, NYC and Cook County | `python code/policy_case_studies.py` |
| `data/policy_rules.csv` (curated by hand, with a source URL per row) | Rental cooling rules and building performance standards | Edit by hand; see `data/policy_sources.md` |

## Cooling gap and extremes (analysis only, not a forecast input)

Used by `code/policy_extremes.py` and `code/policy_cooling_gap.py`. Downloaded at run time and cached in `data/raw/policy/` (not uploaded).

| Source | What we use | Geography | Year | Licence |
|---|---|---|---|---|
| U.S. Census Bureau, Local Air Conditioning Estimates (LACE), [`LACE_23_County.csv`](https://www2.census.gov/programs-surveys/demo/datasets/lace/2023/LACE_23_County.csv) | Occupied households with and without AC (count, %, margin of error) | County | 2023 (released 2026-05-19; experimental, modelled from AHS + ACS) | U.S. Government work |
| CDC/ATSDR Heat & Health Index 2024, [ArcGIS service](https://onemap.cdc.gov/onemapservices/rest/services/Hosted/The_Heat_And_Health_Index/FeatureServer/0) ([technical documentation](https://www.atsdr.cdc.gov/place-health/media/pdfs/2024/07/HHI-2024-Release-Technical-Documentation-508.pdf)) | `p_imperv`, `p_treec` (% of area, NLCD 2021), `p_pov`, `p_iso` (% adults living alone), `p_age65` (ACS 2015-2019), `pr_hri` | ZIP code tabulation area (2010) | 2024 release | U.S. Government work |
| U.S. Census Bureau, [2010 ZCTA-to-county relationship file](https://www2.census.gov/geo/docs/maps-data/data/rel/zcta_county_rel_10.txt) | Population in each ZCTA-county part (`POPPT`), used as weights | ZCTA x county | 2010 | U.S. Government work |

Each city takes the values of its weather station's county (`outputs/policy_check/station_county.csv`); Heat & Health Index values are population-weighted over the county's ZIP code areas. Housing, land cover and population do not respond to the weather, so their year does not matter for the data rule. The 2019-2025 observed heat days are analysis only.
