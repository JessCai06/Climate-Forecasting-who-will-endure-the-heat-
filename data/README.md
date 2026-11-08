# Data card: `data/`

No curated data files are stored here. The forecast code downloads its inputs at run time from the challenge dataset.

## Not uploaded (download instead)

| Source | Exact version | How to download | Why not uploaded |
|---|---|---|---|
| [CMU-OSPO/protostar-climate-train-to-2018](https://huggingface.co/datasets/CMU-OSPO/protostar-climate-train-to-2018): `annual_indices`, `coverage_and_stations` (CC0-1.0), years up to 2018 | the dataset revision is recorded in `outputs/exp03/run_log.json` (`dataset_revision`) | `code/shared.py` `load_train()` (`huggingface_hub.hf_hub_download`, `repo_type="dataset"`) | Public and reproducible. `daily` and `city_info` are not used. |

## How the files fit together
- **Join key:** `ID` (= `city_id` in `submission.csv`) and `Year`.
- **Units:** °F, inches, °F-days, as in the source.
- **Preparation:** `+inf/-inf` in `Max Tmax` (years with every day missing) become NaN. A city-year is valid for a metric if it misses at most 10 days of what the metric needs (`Miss Prcp`; `Miss Tmax`; the larger of `Miss Tmax` and `Miss Tmin`; for `cdd`, days in the year minus `Days Both`). Invalid years are never used.
- **Known limitations:** station records start in different years; some cities have fewer than 10 valid years in 1989-2018 and use a fallback (plain average of the valid years they have).

## Data rule check
- [x] Every forecast input is weather data up to 2018-12-31 (enforced by `shared.assert_cutoff`).
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
