# Experiment 2: Line + Forest hybrid (temperature) and Line (precipitation)

ProtoStar Challenge: Climate Risk Intelligence (CMU-OSPO)
Status: draft spec, 2026-11-07
Challenge deadline: 2026-11-10, 11:59 PM ET
Instructions for: Claude Code, working inside the existing repository

---

## 0. Read this first: how to work in this repo

This file will be dropped into a repository that already has a local scoring script that copies the contest's scoring (the one with the "Starter code (RandomForest)" row, the baselines, and `score(fc)`). You do not know the layout yet.

Before writing any code:

1. Look around. Find the existing scoring script, the truth helpers (likely `code/starter_score.py`, `code/truth.py`, `code/fetch_truth.py`, but check), any shared helpers, and any earlier experiment folders. Follow the naming and folder habits you find. Put new code next to the code it is most like.
2. Run the existing scoring script once, unchanged, and save its printed table. This is your regression check. If you refactor anything, the numbers in that table must not change.
3. Do not edit the existing scorer's behavior. You may add one new model entry to it (section 6) and extract shared helper functions into a small shared module, as long as the regression check still passes.

If something in this spec conflicts with what the repo already does, keep the repo's way, and say so in your final report.

## 1. The idea in plain words

Yearly weather is a slow drift plus a lot of random wiggle. We want to know if a smarter model can beat two very simple ones.

- **Plain average:** every future year equals the city's average. No trend.
- **Plain line:** draw a straight line through the city's recent years and extend it. Captures trend, nothing else.
- **Hybrid (line + forest):** draw the same line, then look at what is left over (how far above or below the line each year was). Train one random forest, shared by all cities, to predict those leftovers from the previous three years' leftovers. Final forecast = line + predicted leftover.

The line handles the trend, which a forest cannot continue by itself. The forest only has to learn the leftovers, which are on a similar scale in every city.

**Rule: the hybrid is kept only if it clearly beats both the plain line and the plain average on held-back past years. Otherwise it is dropped and the plain line (or average, whichever won) is used.** The decision is made by code, by the rule in section 5, and written to a file before anyone looks at 2019-2025 results.

## 2. What gets used for each metric

| Metric code | Column | Method |
|---|---|---|
| `annual_avg_temp` | `Avg Temp` | Hybrid vs plain line vs plain average, decided by the rule in section 5 |
| `total_precip_in` | `ToT Prcp` | Plain line per city, clipped at 0 (no decision rule). Also report plain average for reference only |
| `cdd` | `cdd` | **Assumption:** same decision as temperature, since it is heat-driven. Change in the config if you disagree |
| `hottest_day_temp` | `Max Tmax` | **Assumption:** plain 30-year average, no model (the challenge page says matching the average here is already reasonable) |

Put this table in one config dictionary (e.g. `METRIC_PLAN`) so it can be changed in one place. The scorer needs all four metrics, so every metric gets a method.

## 3. Hard rules (do not break)

- Data cutoff: assert that no year or date in any weather input exceeds 2018. Stop with an error if it does.
- Do not choose or tune anything by looking at 2019-2025 observations. All choices (hybrid vs line vs average, window length, margin) are made only from held-back years inside the training data (section 5).
- The model code must not import or read the truth files (`truth.py`, observation CSVs). Only the scorer reads them.
- Write the forecast file to disk first. The scorer step then reads that file. The 2019-2021 score is analysis only and must never change which method is submitted.
- LLM or agent output may not be used as forecast values. All numbers come from the code and the dataset.
- Fixed random seed: `random_state=42`.

## 4. Data handling (match the existing scorer)

Reuse the existing scorer's rules instead of re-writing them. If its helpers cannot be imported (a script that runs on import cannot be imported cleanly), move the helper functions into a small shared module and import them from both places. Then re-run the regression check.

Rules to match:

- Dataset: `CMU-OSPO/protostar-climate-train-to-2018`, tables `annual_indices` and `coverage_and_stations`. Record the dataset revision in the run log.
- Replace `inf` and `-inf` with NaN (`Max Tmax` has all-missing years stored as `-inf`).
- A city-year is valid for a metric when 10 or fewer days are missing for the values that metric needs:
  - `Avg Temp`: larger of `Miss Tmax` and `Miss Tmin`
  - `ToT Prcp`: `Miss Prcp`
  - `Max Tmax`: `Miss Tmax`
  - `cdd`: days in the year minus `Days Both` from `coverage_and_stations`
- Invalid years become NaN. Do not interpolate for the line. A line can be fitted on the valid points using the year number as the x value.
- A city-metric needs at least 10 valid years in its window to be "scored" by the scorer. Still predict it anyway.

## 5. Held-back test and the decision rule

**Held-back test (the only place choices are made).** Mirror the real task inside the training data.

- Origins: 1998, 2004, 2011. For each origin, use only data up to the origin, then forecast the next 7 years (for 2011 that is 2012-2018).
- Rebuild everything relative to each origin: the line window is the last 30 years up to the origin, the plain average is the mean of valid values in that same window, and the forest is trained only on data up to the origin.
- Score only valid actual years, with the same 10-missing-day rule.
- Pool errors across all scored city-years per metric, then:
  skill = 1 - MAE_method / MAE_plain_average
- Report per origin and the average across origins.

**Decision rule (set these numbers in config before running; do not change them after seeing results).**

The hybrid is kept for a metric only if all three are true:

1. Its average skill across the three origins is higher than both the plain line's and the plain average's.
2. It beats both of them in at least 2 of the 3 origins.
3. Its average skill beats the better of the two by at least `MARGIN = 0.02` (2 skill points).

If any fails, use whichever of the plain line and plain average has the higher average skill for that metric. Write each decision, with the numbers behind it, to `decision.json` before the final forecast is generated.

## 6. How to build each method

**Plain average.** Mean of valid values in the last 30 years up to the origin (1989-2018 for the real forecast). Same value for all 7 years.

**Plain line.** For each city, an ordinary straight-line fit of value against year over the valid years in the 30-year window. Extend it to 2019-2025 using the actual year numbers (this handles trailing missing years correctly). Clip precipitation and cdd at 0.

**Hybrid.**
1. For each city, fit the plain line over its 30-year window. Leftover for each valid year = actual minus line.
2. Build the three previous leftovers for each year **by year number, not by row position**. Re-index each city to every year in its window so a missing year gives NaN, not a shifted row. Drop rows that lack any of the three lags or the leftover itself.
3. Train one `RandomForestRegressor(n_estimators=100, random_state=42)` on all cities together, using only leftovers from inside each city's window. No tuning.
4. For each city, start from its last valid leftovers and predict leftovers forward one year at a time, feeding each prediction back in as the next lag. If the city's last valid year is earlier than the origin, keep stepping through the gap and keep only the 7 forecast years.
5. Forecast = line value + predicted leftover, for each of the 7 years.

Expected behavior, not a bug: the predicted leftovers drift toward 0 later in the horizon, so the hybrid will look more and more like the plain line.

**Fallbacks (no peeking at 2019-2025).** If a city-metric has fewer than 10 valid years in the window, use the plain average of whatever valid years exist. If it has none, use the mean across all cities for that metric and year window. Every row must end up with a finite number.

## 7. What must come out (the contract the scorer will check)

**A. A forecast function** in a new module (suggested name `exp02_line_forest.py`, adapt to repo habits):

```python
def make_forecast(train_df, cov, metric_plan, origin=2018) -> dict:
    """Returns {(city_id, metric): [v2019, v2020, ..., v2025]}, 7 floats, in year order."""
```

The existing scorer reads values as `fc[(city_id, metric)][year - 2019]`, so this exact shape is required. Metric keys are the codes in section 2. Every one of the 210 cities must be present for all four metrics.

**B. A new row in the existing scoring table.** Add one model entry (suggested label `"Line + Forest hybrid (exp02)"`) next to the existing "Starter code (RandomForest)" row, so one run prints all methods side by side. The scorer must keep using the same live years (2019-2021) and the same baseline rules as before.

**C. A submission file**, written by the new code *before* the scorer runs: `submission_exp02.csv`, columns exactly `city_id,year,metric,predicted_value`, years 2019-2025, the four metric codes, 210 x 7 x 4 = 5,880 rows, no empty, NaN or infinite values. `city_id` is the station `ID` (Pittsburgh = `USW00094823`).

**D. Held-back results:**
- `heldout_results.csv`: per metric, per method, per origin: MAE and skill, plus the average across origins.
- `decision.json`: for each metric, the method chosen and the numbers behind the choice.

**E. A run log** `run_log.json`: config (including `MARGIN`, window length, origins, `METRIC_PLAN`), dataset revision, package versions, git commit, timestamp.

## 8. Charts (plain, readable)

Save PNG files to a `charts/` folder next to the other outputs.

1. **Prediction charts, one per metric (4 files, e.g. `pred_annual_avg_temp.png`).** Each file is a 2x2 grid of 4 cities. Each panel shows:
   - the city's valid history (line)
   - the plain average forecast, plain line forecast, and the final chosen method's forecast for 2019-2025, in different line styles with a legend
   - a title with city name, metric, unit
2. **Skill chart (`heldout_skill_by_method.png`).** A column (bar) chart of average held-back skill per metric, one bar per method, with the 30-year average at 0 for reference.

Pick the 4 cities by a deterministic rule, not by hand: Pittsburgh (`USW00094823`), the city with the highest and the lowest mean `Avg Temp` over 1989-2018, and the city with the highest mean `ToT Prcp`. Only use cities with at least 10 valid years in 1989-2018 for all four metrics. Break ties by `ID`.

The charts show history and forecasts only. An optional flag `--overlay-truth` may add the 2019-2021 observations, but only after the forecast file is written, only for analysis, and it must be off by default.

## 9. Acceptance checks (all must pass)

1. The existing scoring script, run unchanged, prints the same numbers as before (regression check).
2. Cutoff guard: the code raises an error if any weather input after 2018 is present.
3. `submission_exp02.csv` has the exact schema in section 7C and passes any submission check script already in the repo (for example `check_submission.py`, if present).
4. `make_forecast` returns 210 cities x 4 metrics x 7 floats, all finite, precipitation and cdd never below 0.
5. The new model's row appears in the scoring table, scored on the same years and cities as the others.
6. `decision.json` was written before the final forecast, and the decision numbers match `heldout_results.csv`.
7. Re-running gives identical forecasts (fixed seed).
8. A search of the model code shows no import or read of the truth files and no use of any year above 2018.
9. All charts in section 8 exist and open.

## 10. Report back (short)

Finish with a few lines: the held-back table (per metric, per method, average skill), which method was chosen per metric and whether the hybrid was dropped, the new row from the scoring table next to the baselines (analysis only), where the chart and CSV files are, and anything you changed in existing files.

## 11. Out of scope

Prediction intervals, outside predictors, ARIMA and other model families, tuning the forest, and any choice made by looking at 2019-2025 observations.

## Sources

- Challenge task and rules: https://huggingface.co/spaces/CMU-OSPO/protostar-challenge-climate-risk-intelligence
- Training data: https://huggingface.co/datasets/CMU-OSPO/protostar-climate-train-to-2018
