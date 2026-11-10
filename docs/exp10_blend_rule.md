# Experiment 10: blended forecast. Decision rule (written before the code was run, 2026-11-10)

**Idea.** Every earlier experiment picked one method per metric. Averaging methods whose errors are only partly alike usually lowers error a little. Experiment 5's equal-weight ensemble was tested and not chosen, so this tests a *weighted* blend.

**Data rule.** Only data up to 2018-12-31 (challenge dataset, pinned revision). No observation from 2019 on is read by this experiment. Scoring against NOAA observations happens only after the forecast is frozen and never changes the decision.

**Pool, per metric** (all candidates already built in Experiments 5 and 5B, nothing new):
- every metric: plain average (`avg`), recent 10- and 15-year means (`r10`, `r15`), shared slope (`shared`), recent level + shared slope (`r10s`, `r15s`)
- temperature also: station-aware level (`stn`)
- hottest day also: 95th-percentile versions (`h30p95`, `h15p95`)
- cdd also: scaled slope (`scaled`, `r15sc`) and the daily-data delta method (`cdd10d`, `cdd15d`); `avg`, `r10`, `r15` are dropped for cdd to keep the pool at 8

**Weights.** Non-negative, sum to 1, on a grid of steps of 0.1 (coarse on purpose). Chosen to minimise the average over the origins 1998, 2004 and 2011 of (blend MAE / plain-average MAE), using the same city-years and the same scoring as Experiment 5.

**Honest test (leave one origin out).** For each origin, weights are fitted on the other two origins and the blend is scored on the origin that was left out. A blend's skill is the average of those three out-of-sample skills.

**Rule, per metric.** The blend replaces the current method (the Experiment 5B pick: temperature `r15s`, precipitation `avg`, hottest day `avg`, cdd `cdd10d`) only if both hold:
1. its leave-one-origin-out average skill beats the current method's average skill by at least 0.01, and
2. it beats the current method in at least 2 of the 3 left-out origins.

Otherwise the current method is kept for that metric. The final blend weights, if used, are fitted on all three origins and applied to the origin-2018 forecasts of the pool.

**Fallback.** If no metric passes, `submission.csv` (Experiment 5B, commit `0fbbe5b`) stays as it is and nothing new is submitted.

**Scoring afterwards (analysis only).** The result is scored with `code/starter_score.py` on 2019-2021 (the live window) and 2022-2025, next to Experiments 5 and 5B, and declared in the README whatever it shows.
