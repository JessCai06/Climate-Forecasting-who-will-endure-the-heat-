# Experiment 5: Fill missing days from NOAA nClimGrid-Daily, then rerun Experiment 3

ProtoStar Challenge: Climate Risk Intelligence (CMU-OSPO)
Status: draft spec, 2026-11-08
Challenge deadline: 2026-11-10, 11:59 PM ET
Instructions for: Claude Code, working inside this repository
Category: **coverage** (rebuild each city's own record). Borrowing trends from other places (Exp04's regional slopes) is the separate "geographic" category and is out of scope here.

---

## 0. Read this first

The repo layout is known:

- `code/shared.py`: `load_train`, `valid_flags`, `METRICS`, `assert_cutoff`, `dataset_revision`.
- `code/exp02_line_forest.py`: constants (`WINDOW=30`, `ORIGINS=[1998, 2004, 2011]`, `H=7`, `MIN_VALID=10`, `CLIP0`, `SEED=42`) and helpers (`to_rows`, `_window_series`, `git`).
- `code/exp03_shared_slope.py`: the submitted method. Exp05 changes **only the data it is fed**, not the method.
- `code/exp04_neighbors.py`: the masking test and the neighbor gap fill. Reuse its structure where it fits.
- `code/AGENTS.md`: the data rule. Read it; this spec does not override it.

Before writing code:

1. **Regression check.** Run `python code/exp03_shared_slope.py` unchanged and confirm its output equals `submission.csv`. Run `python code/starter_score.py obs_2018_2021.csv` and save the table. If you refactor anything, both must stay the same.
2. Do not change the behavior of any existing script. You may add one row to the scorer, as Exp04 did.

If something here conflicts with the repo's way, keep the repo's way and say so in the report.

## 1. The idea in plain words

About 5% of city-years in 1989-2018 are thrown away because the station missed more than 10 days of a metric's data. Of the 304 invalid temperature city-years, 164 missed only 11-90 days; the station has most of the year. Exp03 drops these years whole.

Instead: fill each **missing day** with the value NOAA's gridded daily dataset (nClimGrid-Daily) gives for the station's location, corrected for the usual difference between that station and the grid. Then recompute the four yearly metrics from the completed daily record and rerun Exp03's method on it.

Keeping the station's real days matters most for `hottest_day_temp` (a missing day may have been the hottest) and for years where a long gap made the whole year unusable.

**Rule: the filled data replaces Exp03's data for a metric only if it clearly beats Exp03 on held-back past years (section 7).** Otherwise Exp03 stays. This is decided by code and written to `decision.json` before the final forecast.

Honest expectation: Exp04's neighbor fill gained only +0.0007 temperature skill. The gain here may be just as small overall. Report the cities with gaps separately (section 7) so a real local gain is visible.

## 2. Data

| Source | What | Use |
|---|---|---|
| Challenge dataset `CMU-OSPO/protostar-climate-train-to-2018`, table `daily` | Station daily `tmax`, `tmin` (°F), `prcp` (in), columns `ID, Name, Date, tmax, tmin, prcp`. Not used by earlier experiments. | The station's real days. |
| Same dataset, `annual_indices`, `coverage_and_stations`, `city_info` | Yearly metrics, missing-day counts, station segments | Check the rebuild (step 1); `city_info` station dates for reference. |
| **NOAA nClimGrid-Daily** (NCEI) | Gridded daily Tmax, Tmin, Prcp for the lower 48 states, about 5 km, from GHCN-Daily stations | Fill missing days. |

nClimGrid-Daily details to **verify from NOAA's own page before use, not from memory**: start year, grid spacing, units (expected °C and mm; convert to °F and inches), file layout, official download location, license. Record the exact URL, product version and download date in `run_log.json` and `data/README.md`.

All 210 cities are in the lower 48 states (lat 24.6-48.6, lon -124.2 to -70.3), so the grid covers every city.

**Download only what is needed:**
- Years 1969-2018. The earliest window is 1969-1998 for origin 1998. Set the end date to 2018-12-31 on every request, and assert after loading that no date is later than 2018-12-31.
- Only the 210 grid points. Use the cell containing the city's `Lat`/`Lon` from `annual_indices`. If that cell has no data (coast, e.g. Key West), use the nearest cell with data, and log which cities moved and by how far.
- Save the extracted point series to `data/cache/nclimgrid_points.parquet` (add `data/cache/` to `.gitignore`). Describe it in `data/README.md` under "Not uploaded (download instead)" with the script that rebuilds it.

## 3. Hard rules (do not break)

- Every weather input is dated on or before 2018-12-31. Assert it for the station daily table and for nClimGrid. Stop with an error otherwise.
- No choice is made from 2019-2025 observations. All choices come from the masking test (step 4) and the held-back test (step 6).
- Model code must not import or read `truth.py`, `fetch_truth.py`, `obs_*.csv` or any answer key.
- **As-of-origin calibration.** For held-back origin O, the station-minus-grid correction is estimated only from days up to O. Never use later days to correct earlier ones.
- **Truth is real data only.** Held-back scoring uses only city-years that are valid under the original 10-day rule using real station data. Filled values are never scored.
- Fixed seed 42. Re-running must give identical files.
- No forecast value from an LLM or a web search. Every number comes from the code and the data.

## 4. Steps

### Step 1. Rebuild the yearly metrics from the daily table (must pass before anything else)

Write `annual_from_daily(daily_df)`, which returns per city-year the four metrics and the missing-day counts:

- `Avg Temp`, `ToT Prcp`, `Max Tmax`, `cdd`; `Miss Tmax`, `Miss Tmin`, `Miss Prcp`, `Days Both`.
- Find the exact definitions by matching `annual_indices`. Avg temp is probably the mean of daily (tmax+tmin)/2 or the mean of `Avg Tmax` and `Avg Tmin`. cdd is probably the sum of max(0, (tmax+tmin)/2 − 65). Test the candidates; do not assume.

Compare against `annual_indices` and `coverage_and_stations` for 1969-2018 and write `reconstruction_check.csv` (per metric: rows compared, share matching within tolerance, worst difference). Tolerance: 0.01 for temperatures and inches, 0.5 for cdd. Missing-day counts must match exactly.

**Stop and report if fewer than 99% of valid city-years match for any metric.** Everything after this depends on the rebuild being right.

### Step 2. Station-to-grid correction

For each city and each calendar month, using days where both the station and the grid have a value:

- `tmax`, `tmin`: correction = mean(station − grid). Filled value = grid + correction.
- `prcp`: correction = ratio of monthly totals (station / grid), limited to [0.5, 2.0]; use 1.0 if the grid total is 0. Filled value = grid × ratio.

Estimate it **as of each origin**, from the last 10 years of overlap up to the origin (origin 2018 uses 2009-2018). If fewer than 3 years of overlap exist for a month, use the city's all-month correction. Write `calibration.csv` (origin, city, month, variable, correction, overlap days).

Use the most recent 10 years, not all years: station moves (see `Station Changes` in `coverage_and_stations`) can shift the difference, and recent years are the most relevant to the forecast.

### Step 3. Complete the daily record and recompute the metrics

For origin O:

1. Take the station's daily record for the window.
2. Fill every missing `tmax`, `tmin`, `prcp` day with the corrected grid value. Keep every real station day as it is.
3. Recompute the four metrics with `annual_from_daily`.
4. For each city-year-metric keep `n_filled_days` (days filled for the variables that metric needs) and flag `is_filled = n_filled_days > 10`. Years with 10 or fewer filled days were already valid; keep their **original** `annual_indices` values so nothing changes for them.

Write `filled_years.csv` for origin 2018: city, year, metric, original value (NaN if invalid), filled value, `n_filled_days`.

### Step 4. Masking test (choose the fill before any forecast)

Check how accurate the fill is on days where the truth is known. Use origin 2018 and the window 1989-2018.

- **Hide in realistic shapes,** because real gaps come in runs: (a) random 30-day blocks, (b) random 90-day blocks, (c) whole years. For each shape, pick 15% of fully valid city-years (seed 42) and hide that block's station days.
- Fill the hidden days and recompute the yearly metrics. Compare with the real yearly value.
- Compare these fills:
  1. corrected grid (step 2), with the correction estimated without the hidden days;
  2. raw grid (no correction);
  3. for whole years only: Exp04's neighbor fill (`exp04_neighbors.fill_gaps`, its chosen limits) and linear interpolation of the city's yearly series.
- Write `masking_test.csv`: shape, metric, fill method, n, MAE.
- Choose corrected vs raw grid per metric by the lowest MAE across the three shapes pooled (ties: raw, the simpler). Write the choice to `fill_method.json` **before any forecast**.

**Known optimism, state it in the report:** NOAA builds nClimGrid partly from these same stations. When a day is hidden here, the grid still "saw" it, so this test overstates accuracy. On days that are truly missing, the grid relies on neighbors only and will be less accurate. Optional section 9 gives an honest check.

### Step 5. Candidates

Each candidate keeps **Exp03's chosen method per metric** (shared slope for `annual_avg_temp` and `cdd`, plain average for `total_precip_in` and `hottest_day_temp`) and changes only the data:

| Code | Name | Slope from | Level (mean and mean year) from |
|---|---|---|---|
| `X0` | Exp03 as submitted | real valid years | real valid years |
| `X1` | Filled level | real valid years | real valid + filled years |
| `X2` | Filled all | real valid + filled years | real valid + filled years |

For plain-average metrics, `X1` and `X2` are the same (no slope), so report one of them.

A city-metric with fewer than 10 valid years keeps Exp03's fallback under `X0`. Under `X1`/`X2`, filled years count toward the 10, so some of the 9 fallback city-metrics will get the full method. List which ones.

Put the candidates in one config dictionary so they can be changed in one place.

### Step 6. Held-back test

As in Exp03: origins 1998, 2004, 2011, forecast the next 7 years. Everything (correction, filling, slope, level) is rebuilt as of each origin. Score against **real valid station values only**, on exactly the same city-years as Exp03, so the numbers are directly comparable with `outputs/exp03/heldout_results.csv`. Regression check: `X0` must reproduce Exp03's held-back MAE exactly.

skill = 1 − MAE / MAE of the plain average (same as Exp03). Also report **gain = skill(candidate) − skill(X0)** per origin and on average.

Also report the same numbers for the subset of city-metrics with any gap in their window (the "a" group in `outputs/exp04/step0_counts.csv`). This subset is for the report only and **does not drive the decision**.

## 7. Decision rule (fixed before running; do not change after seeing results)

For each metric, a filled candidate replaces `X0` only if all of these hold:

1. Its average gain over `X0` is at least `MARGIN = 0.01`. This is the same 0.01 used in Exp03's close-call rule. The team may change it **before** running, not after.
2. It beats `X0` in at least 2 of the 3 origins.
3. If both `X1` and `X2` pass, take the one with the higher average gain. If they are within 0.01 of each other, take `X1` (filled values touch less).

Otherwise keep `X0` for that metric. Write each decision with the numbers behind it to `decision.json` before the final forecast.

## 8. Outputs (`outputs/exp05/`)

In writing order:

1. `reconstruction_check.csv` (step 1)
2. `calibration.csv` (step 2, all origins)
3. `masking_test.csv` and `fill_method.json` (step 4, before any forecast)
4. `heldout_results.csv`: per metric, candidate, origin (and average) and subset (all / gap cities): MAE, skill, gain over X0, n
5. `decision.json` (before the final forecast)
6. `submission_exp05.csv`: the chosen plan. Exact schema `city_id,year,metric,predicted_value`, 5,880 rows, finite, precip and cdd ≥ 0. Also `submission_exp05_X1_all.csv` and `submission_exp05_X2_all.csv`, each applying one candidate to every metric, for comparison.
7. `filled_years.csv` (origin 2018)
8. `run_log.json`: config, nClimGrid source URL, version and download date, dataset revision, package versions, git commit, timestamp.
9. Scorer: add rows labelled `Exp05 chosen per metric`, `Exp05 X1 filled level (all)`, `Exp05 X2 filled all (all)`, in the same way Exp04 added its rows. Save the printed table as `scorer_after.txt`. **Analysis only; it must not change the decision or the submission.**

Charts (`outputs/exp05/charts/`), plain and readable:
- `masking_mae.png`: MAE per fill method, per metric, per hidden shape.
- `filled_examples.png`: 4 cities with the most filled years. Real yearly values as dots, filled years as hollow dots, Exp03 and Exp05 forecasts as lines.
- `heldout_gain.png`: average gain over X0 per metric and candidate, all cities vs gap cities.

## 9. Optional, only if time allows: an honest accuracy check

The masking test in step 4 is optimistic (see there). For an honest number, build a small "mesh" from GHCN-Daily stations **other than** the target city's station: those within 100 km with at least 15 years of overlap, up to 2018-12-31 only. Fill the hidden blocks by inverse-distance-weighting their daily anomalies, then compare with step 4's nClimGrid MAE.

This is for reporting only and does not change any decision. Time-box it: skip it if the main steps are not done by 2026-11-09 evening.

## 10. Acceptance checks (all must pass)

1. The regression checks in section 0 still pass (Exp03 reproduces `submission.csv`; the scorer's existing rows are unchanged).
2. Step 1 rebuild matches at least 99% for every metric.
3. The cutoff guards stop on any date after 2018-12-31, for both station and grid data.
4. Held-back `X0` equals Exp03's held-back MAE exactly.
5. `fill_method.json` was written before any forecast, and `decision.json` before the final forecast (check the file times or the order in the log).
6. `submission_exp05.csv` passes `python code/check_submission.py outputs/exp05/submission_exp05.csv`.
7. Model code reads no truth file and no year above 2018 (search the code).
8. Re-running gives identical files.
9. `data/README.md` lists nClimGrid-Daily with source, version, years and how to rebuild the cache.

## 11. Report back (short)

- Rebuild match rates.
- Masking-test MAE: corrected grid vs raw grid vs Exp04 neighbor fill vs interpolation.
- The held-back table (per metric, per candidate: average skill and gain over X0), for all cities and for the gap cities.
- The decision per metric and why.
- Which fallback cities got the full method.
- The scorer rows (analysis only).
- The optimism caveat from step 4.
- Any change to existing files.

If Exp05 is chosen for any metric, **do not overwrite `submission.csv`.** Stop, and let a team member decide whether to submit it and update the README (method, external sources, data card).

## 12. Out of scope

Regional or neighbor-pooled slopes (geographic category, Exp04), adjusting levels for station moves, other gridded products (PRISM, Daymet, ERA5), new forecast methods, and any choice made from 2019-2025 observations.

## Sources

- Challenge task and rules: https://huggingface.co/spaces/CMU-OSPO/protostar-challenge-climate-risk-intelligence
- Training data: https://huggingface.co/datasets/CMU-OSPO/protostar-climate-train-to-2018
- nClimGrid-Daily: NOAA NCEI. Find the official product page and record the exact URL in `run_log.json`; do not rely on a remembered address.
