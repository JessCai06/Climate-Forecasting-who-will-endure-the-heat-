# Protostar Challenge: Climate Risk Intelligence (CMU 2026)

Negative result: no

Links: [submission template](https://huggingface.co/datasets/CMU-OSPO/protostar-climate-submission-template) · [challenge Space](https://huggingface.co/spaces/CMU-OSPO/protostar-challenge-climate-risk-intelligence)

`submission.csv` holds our forecasts: 210 cities × 7 years (2019-2025) × 4 metrics = 5,880 rows. It is the Experiment 3 forecast, frozen in commit `295c10ab5e8eeb4e81b116688f3632ade49366d7`.

## Method

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

**Reproduce:** `pip install -r code/requirements.txt`, then `python code/exp03_shared_slope.py` writes `outputs/exp03/submission_exp03.csv`, which is identical to `submission.csv`. Check with `python code/check_submission.py submission.csv`. The run takes about a minute and a half and has a fixed seed (42).

## External sources

**Forecast inputs:** none beyond the challenge dataset `CMU-OSPO/protostar-climate-train-to-2018` (tables `annual_indices` and `coverage_and_stations`, years up to 2018). No other data is used as a forecast input.

**Policy analysis only** (never read by the forecast code): NOAA GHCN-Daily observations 2019-2025 for the 210 stations; Census ACS 5-year 2019-2023 tables B25024, B25034, B25003 (all counties); FCC Area API (station to county); Allegheny County Property Assessments (WPRDC); NYC PLUTO; Cook County Assessor improvement characteristics; rental cooling rules and building performance standards compiled by hand in `data/policy_rules.csv` (a source URL per row). Details and how to download each: `data/README.md` and `data/policy_sources.md`.

## Post-hoc scoring declaration

After the forecast was frozen and committed (commit `295c10ab5e8eeb4e81b116688f3632ade49366d7`), we scored it against NOAA GHCN-Daily observations for 2019-2021 (the live window), only for analysis. These observations were never an input to any forecast and **never changed any choice**: every decision above was made on the held-back years 1998, 2004 and 2011. The scoring code is `code/fetch_truth.py`, `code/truth.py` and `code/starter_score.py`; the model code does not read them. We built the 2019-2021 values from NOAA because the official answer key is not public to us. Our reproduction of the leaderboard's "10-year mean" reference row gives the same score (10.4) with error values within about 1-2% of the reference, so treat our numbers as approximate.

Analysis-only live scores (2019-2021, our NOAA-based truth):

| Model | Score | Avg temp MAE °F | Precip MAE in | Hottest day MAE °F | CDD MAE °F-days |
|---|---|---|---|---|---|
| 30-year average (reference) | 0.0 | 1.474 | 5.983 | 2.164 | 197.700 |
| Exp03 chosen per metric (this submission) | 13.8 | 1.068 | 5.983 | 2.164 | 142.756 |

## AI Tools and Agents

- **Tool and model:** Claude Code (Anthropic's CLI agent) running Claude Sonnet 5.5 (`claude-sonnet-5-5`), inside VS Code.
- **What it did:** wrote the code in `code/` from the team's written specs (`exp02_line_forest_hybrid_spec.md` and the Experiment 3 instructions); ran the experiments and the post-hoc scorer; extracted shared helpers; made the charts; drafted this README and the data card; set up the commit. For the policy analysis it searched for and tested building and policy data sources, wrote `code/census_acs.py`, `code/policy_case_studies.py` and `code/policy_check.py`, compiled `data/policy_rules.csv` from web search results (each row cites its source), and drafted the Policy Idea from the team's direction (Pittsburgh, small mixed-use buildings).
- **What it did not do:** it supplied no forecast values. Every `predicted_value` comes from the code and the dataset. It downloaded no weather after 2018 for any forecast. Post-2018 NOAA data was used twice, both approved by a team member and both analysis only: the post-hoc scoring above (2019-2021) and the policy analysis (2019-2025).
- **What a person did and reviewed:** [TEAM: confirm and edit. The team wrote the specs, decided the rules and settings, and approved the NOAA download for scoring. Add what you personally reviewed, for example the decision rule, the outputs or the README.]
- **Without the agent:** the code reproduces `submission.csv` without the agent (see Reproduce above). `code/AGENTS.md` holds the agent's data rule.

## Policy Idea

**Cool the shop-houses: heat-pump retrofits for small mixed-use buildings in Pittsburgh.**

**The risk.** Air-conditioning demand is rising faster than buildings were designed for, while peak heat has barely moved. Across 210 U.S. cities, cooling degree days (CDD) in 2019-2025 were a median 22% above 1976-2005 (higher in 97% of cities), but the hottest day rose only about 1 °F. Pittsburgh's CDD rose 28% (735 to 941), and our forecast, made with data only up to 2018, expected this rise (981). The trend in cooling load is predictable; peak days are not. The buildings most exposed are often left out of policy. Pittsburgh has 1,683 "retail/office with apartments over" buildings, typically owned by small local landlords. They fall far below the city's 50,000 sq ft benchmarking threshold, no rental cooling rule covers them, and the county records a build year for only 2.4% of them.

**What to do, and who.** The City's Office of Sustainability and Duquesne Light would offer a one-stop "shop-house" retrofit: a cold-climate heat pump plus roof insulation and shading, paid through **on-bill financing**, so monthly payments stay below the energy savings and the charge stays with the meter, not the owner. Allegheny County's Office of Property Assessments would record building age, floor area and cooling for mixed-use parcels, so the program can find and track them.

**Why it is sustainable.** Pittsburgh is heating-dominated, so one heat pump replaces gas heating *and* inefficient window AC: emissions fall even as cooling demand rises. On-bill repayment from savings needs no ongoing subsidy, and better envelopes keep bills lower in each warmer year. It plans for the predictable trend rather than a predicted heat wave.

*Evidence: `outputs/policy_check/thesis_check.md` (code: `code/policy_check.py`, `code/policy_case_studies.py`). The 2019-2025 values are observed NOAA data, used for this analysis only, never as a forecast input.*

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
