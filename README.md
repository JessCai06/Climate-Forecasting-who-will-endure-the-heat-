# Protostar Challenge: Climate Risk Intelligence (CMU 2026)

Negative result: no

Links: [submission template](https://huggingface.co/datasets/CMU-OSPO/protostar-climate-submission-template) · [challenge Space](https://huggingface.co/spaces/CMU-OSPO/protostar-challenge-climate-risk-intelligence)

`submission.csv` holds our forecasts: 210 cities × 7 years (2019-2025) × 4 metrics = 5,880 rows. It is the Experiment 5 forecast, frozen in commit `caccb0427a8821fe44c9e36767586e780cd1fb85`. (The earlier submission, Experiment 3, was frozen in `295c10ab5e8eeb4e81b116688f3632ade49366d7`.)

## Method (current submission: Experiment 5)

Experiment 5 keeps Experiment 3's shared slope (below) but changes the city's **level**. Experiment 3 starts from the 30-year mean, which is centered on about 2003, so every forecast leans on the slope for 16-22 years. Experiment 5 also tries the mean of the city's last 10 or 15 valid years, the window lengths of NOAA's Optimal Climate Normals (Huang, van den Dool & Barnston 1996, *J. Climate* 9:809-817), with the shared slope continued from those years' middle year. It also tried a station-aware level (years at the city's latest station only), a cdd slope scaled by each city's own cdd-per-°F sensitivity, and an equal-weight ensemble. Same held-back origins, same decision rule as Experiment 3, fixed before running; `outputs/exp05/decision.json` was written before the final forecast.

| Metric | Method used | Held-back skill: chosen (Exp03's pick) | Beat Exp03's pick in |
|---|---|---|---|
| `annual_avg_temp` | **15-year level + shared slope** | +0.177 (+0.157) | 3 of 3 origins |
| `cdd` | **10-year level + shared slope** | +0.086 (+0.070) | 3 of 3 origins |
| `total_precip_in` | **A plain average** | 0 (0) | nothing beat the plain average |
| `hottest_day_temp` | **A plain average** | 0 (0) | nothing beat the plain average |

Full results for all ten candidates: `outputs/exp05/heldout_results.csv`.

**Experiment 6 (nearby stations, not chosen).** We added up to 8 NOAA GHCN-Daily stations within 100 km of each city (1,396 stations, 1969-2018, every download capped at 2018-12-31; see `data/README.md`) and used their averaged anomalies for a regional level or a regional slope. None of the four regional candidates beat Experiment 5's picks on held-back years (best: temperature +0.162 vs +0.177, cdd +0.080 vs +0.086), so its forecast is identical to Experiment 5's. Our reading: the target is one station's own record, and part of a station's recent shift is local (site changes, growth around the airport), which averaging with neighbors dilutes. Code: `code/exp06_*.py`; outputs: `outputs/exp06/`.

## Method of the earlier submission (Experiment 3)

We forecast each metric from the city's last 30 valid years (1989-2018). A year is valid if the station missed at most 10 days of the data that metric needs. Invalid years are never used.

Four simple ideas were compared for every metric:

- **A. Plain average:** the city's 30-year mean, the same for all seven years.
- **B. Own line:** a straight line through the city's own years, extended forward.
- **C. Shared slope:** one slope for all cities (fitted on every city's values after removing that city's own mean and mean year). Each city keeps its own level: `city mean + shared slope × (year − city mean year)`.
- **D. Half slope:** each city's own slope times 0.5, with the same pivot as C.

Precipitation and cdd are clipped at 0. A city with fewer than 10 valid years in the window uses the plain average of the valid years it has (or the all-city mean if it has none).

**How the choice was made.** We used only held-back years inside the training data: for the origins 1998, 2004 and 2011 we used data up to the origin, forecast the next 7 years, and scored them. Skill = 1 − MAE / MAE of the plain average, pooled over scored city-years. The rule, fixed before running: take the idea with the highest average skill; it must beat the plain average in at least 2 of 3 origins (otherwise use the plain average); if it leads the runner-up by less than 0.01, take the simpler idea (order A, B, D, C). `outputs/exp03/decision.json` was written before the final forecast.

| Metric | Method used | Average held-back skill (A / B / C / D) |
|---|---|---|
| `annual_avg_temp` | **C shared slope** | 0 / +0.135 / +0.157 / +0.129 |
| `cdd` | **C shared slope** | 0 / +0.045 / +0.070 / +0.054 |
| `total_precip_in` | **A plain average** | 0 / −0.083 / −0.020 / −0.020 |
| `hottest_day_temp` | **A plain average** | 0 / −0.083 / −0.017 / −0.011 |

For temperature and cdd the shared slope beat the plain average in all three origins. For precipitation and hottest day no trend idea beat the plain average on held-back years, so the plain average is used. Full per-origin MAE and skill: `outputs/exp03/heldout_results.csv`.

An earlier experiment (exp02: line + random-forest hybrid) was dropped by its own held-back rule; its code and outputs are in `code/exp02_*.py` and `outputs/exp02/`.

**Reproduce:** `pip install -r code/requirements.txt`, then `python code/exp05_levels_slopes.py` writes `outputs/exp05/submission_exp05.csv`, which is identical to `submission.csv` (about a minute; no randomness). Experiment 6: `python code/exp06_fetch_neighbors.py` (about 35 minutes of downloads, or uses the curated `data/neighbors/` files), then `python code/exp06_neighbors.py`. Experiment 3: `python code/exp03_shared_slope.py` writes `outputs/exp03/submission_exp03.csv`. Check with `python code/check_submission.py submission.csv`. The run takes about a minute and a half and has a fixed seed (42).

## External sources

- The challenge dataset `CMU-OSPO/protostar-climate-train-to-2018` (tables `annual_indices` and `coverage_and_stations`, years up to 2018): the only input to the submitted forecast.
- NOAA NCEI GHCN-Daily (Menne et al. 2012), daily TMAX/TMIN/PRCP for 1,396 nearby stations, 1969-2018 only: input to Experiment 6's candidates, none of which was chosen. Station list and yearly values are in `data/neighbors/`; see `data/README.md`.

## Post-hoc scoring declaration

After the forecast was frozen and committed (commit `295c10ab5e8eeb4e81b116688f3632ade49366d7`), we scored it against NOAA GHCN-Daily observations for 2019-2021 (the live window), only for analysis. These observations were never an input to any forecast and **never changed any choice**: every decision above was made on the held-back years 1998, 2004 and 2011. The scoring code is `code/fetch_truth.py`, `code/truth.py` and `code/starter_score.py`; the model code does not read them. We built the 2019-2021 values from NOAA because the official answer key is not public to us. Our reproduction of the leaderboard's "10-year mean" reference row gives the same score (10.4) with error values within about 1-2% of the reference, so treat our numbers as approximate.

Analysis-only live scores (2019-2021, our NOAA-based truth):

| Model | Score | Avg temp MAE °F | Precip MAE in | Hottest day MAE °F | CDD MAE °F-days |
|---|---|---|---|---|---|
| 30-year average (reference) | 0.0 | 1.474 | 5.983 | 2.164 | 197.700 |
| Exp03 chosen per metric (earlier submission) | 13.8 | 1.068 | 5.983 | 2.164 | 142.756 |
| Exp05 chosen per metric (this submission) | 14.1 | 1.074 | 5.983 | 2.164 | 139.982 |

Experiment 5 was scored this way only after it was frozen in commit `caccb0427a8821fe44c9e36767586e780cd1fb85`; the score did not change any choice. On 2019-2021 its cdd error is lower than Experiment 3's (140.0 vs 142.8 °F-days) and its temperature error slightly higher (1.074 vs 1.068 °F); three years is a small sample, and the final score uses 2022-2025. Full table: `outputs/exp05/scorer_posthoc.txt`. (With scikit-learn 1.9.1 the starter-code reference row reads 3.5 instead of 3.7; the other rows are unchanged.)

## AI Tools and Agents

- **Tool and model:** Claude Code (Anthropic's CLI agent) running Claude Sonnet 5.5 (`claude-sonnet-5-5`), inside VS Code.
- **What it did:** wrote the code in `code/` from the team's written specs (`exp02_line_forest_hybrid_spec.md` and the Experiment 3 instructions); ran the experiments and the post-hoc scorer; extracted shared helpers; made the charts; drafted this README (except the Policy Idea) and the data card; set up the commit.
- **Experiments 5 and 6:** Claude Code in the Claude desktop app, running Claude Opus 5.5 (`claude-opus-5-5`). It suggested the candidate ideas (recent level, station-aware level, scaled cdd slope, nearby stations) and the external data sources, wrote `code/exp05_*.py` and `code/exp06_*.py`, downloaded the GHCN-Daily station data with a server-side end date of 2018-12-31, ran the held-back tests, and updated this README and the data card. It checked that Experiment 3 reproduces exactly before building on it, and that Experiment 5's version of the shared slope matches Experiment 3's to the last digit.
- **What it did not do:** it supplied no forecast values. Every `predicted_value` comes from the code and the dataset. It downloaded no weather after 2018 for any forecast; the one use of post-2018 NOAA data was the post-hoc scoring above, approved by a team member and used only for analysis.
- **What a person did and reviewed:** [TEAM: confirm and edit. The team wrote the specs, decided the rules and settings, and approved the NOAA download for scoring. Add what you personally reviewed, for example the decision rule, the outputs or the README.]
- **Without the agent:** the code reproduces `submission.csv` without the agent (see Reproduce above). `code/AGENTS.md` holds the agent's data rule.

## Policy Idea

<!-- TEAM TO WRITE (half a page at most): 1. What risk did you notice? 2. What would you do about it, and who would do it? 3. Why is it sustainable? -->

**[TO BE WRITTEN BY THE TEAM. Left empty on purpose.]**

## Feedback to the Ecosystem

Items from real friction in this repo. Each has a way to check it.

1. **`Max Tmax` stores `-inf` for years with no valid days; the starter code crashes on it.** 1,184 rows in `annual_indices` (e.g., `USC00380072`, 1895-1899) have `Max Tmax = -inf`. `RandomForestRegressor.fit` on the starter code fails with "Input y contains infinity". Fix: store NaN. *Verify:* `np.isinf(annual['Max Tmax']).sum()` after loading `annual_indices`.
2. **The starter code stops at "Predict 2019-2025 iteratively ... `# ...`".** There is no complete reference loop, so scores from different teams depend on how each wrote it. A full runnable starter, or a published reference script for the "example notebook" row, would help. *Verify:* open the starter code in the Space's Data & submission tab.
3. **The answer key is private, so the live score cannot be reproduced locally.** `hf_hub_download('CMU-OSPO/protostar-climate-ground-truth', 'answer_key.csv', repo_type='dataset')` fails without a token ("Invalid username or password"). We rebuilt 2019-2021 truth from NOAA, which matches the leaderboard reference only approximately. A public set of aggregated truth for the live years, or a documented scoring script, would remove this. *Verify:* run the call above without a token.
4. **The leaderboard's "10-year mean · example notebook" row is not defined precisely.** We assumed the mean of the valid years 2009-2018. It reproduces the Score (10.4) but not the four MAE values exactly (e.g., precipitation 5.802 vs 5.782). *Verify:* `python code/starter_score.py <obs csv>` prints our row next to the reference.
5. **Validity for `cdd` has no column of its own.** The 10-day rule for `cdd` has to be derived as days in the year minus `Days Both` from `coverage_and_stations`, and for average temperature as the larger of `Miss Tmax` and `Miss Tmin`. This is our reading of the rules (the challenge text does not spell it out per column). *Verify:* see `shared.valid_flags`; we could not check it against the organizers' implementation.

## Files

- `submission.csv`: the forecast (5,880 rows).
- `code/`: `exp03_shared_slope.py` (the method), `exp02_line_forest.py` (reused helpers and the dropped hybrid), `shared.py`, charts and report scripts, post-hoc scoring (`starter_score.py`, `truth.py`, `fetch_truth.py`), `check_submission.py`, `AGENTS.md`, `requirements.txt`.
- `data/README.md`: data card (no data files; inputs are downloaded at run time).
- `outputs/exp03/`: held-back results, decision, run log, charts. `outputs/exp02/`: the earlier experiment.
