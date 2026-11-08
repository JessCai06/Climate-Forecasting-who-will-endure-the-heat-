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
