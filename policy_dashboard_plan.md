# Plan: cooling-readiness dashboard for the cities most in need

**Question.** In the 8 cities where the most people face new heat without air conditioning, if those homes gained cooling, would it hold up? The dashboard checks three things for each city: the homes' wiring, the grid's summer peak and household bills. Every number on the dashboard shows how sure we are of it.

This replaces the single-city Seattle idea. Seattle stays in as one of the 8 cities.

---

## 1. How the pieces relate

```
                 NEED (who is exposed)
   forecast heat days  x  share without AC  x  vulnerability
                         |
                         v
          LOAD if the gap is closed (one shared input)
   households without AC x adoption x kW per unit x kWh per season
           |                    |                      |
           v                    v                      v
   A. HOMES               B. GRID                C. BILLS
   can the wiring         can the summer         can households
   take it?               peak take it?          pay for it?
           |                    |                      |
           +--------------------+----------------------+
                                v
            VERDICT per city and test: holds / strained / fails
            + CONFIDENCE (A/B/C) on every input and verdict
```

The **load** step links them. The same count of households without AC drives all three tests:

- **Homes:** how many panels need upgrading before a unit can be installed.
- **Grid:** how many MW are added at the summer peak.
- **Bills:** how many kWh, and so how many dollars, each household adds per season.

A city can pass one test and fail another. For example, a winter-peaking hydro utility has summer headroom on the grid, but its old housing stock needs panel upgrades. The dashboard's main view is that pattern, laid out as a city-by-test matrix.

---

## 2. Choosing the cities (rule fixed before the grid results)

Start from `outputs/cooling_gap/city_cooling_gap.csv` (199 cities).

1. Keep cities with **at least 10,000 households without AC**. This drops small towns such as Clayton (299 households).
2. Rank by the mean of two ranks:
   - uncooled heat-days per household (`gap_per_household`);
   - total uncooled household heat-days (`gap_households`).
3. **Corroboration filter:** drop a city whose observed heat days in 2019-2025 fell below its 1976-2005 baseline. The heat risk did not show up there, so the city does not belong in a list of cities most in need.
4. Take the **top 8** that pass.

Result (computed from the existing CSV; team decision, 2026-11-09):

| # | City | No AC % | Households without AC | Heat days/yr: 1976-2005, forecast, observed | Note |
|---|---|---|---|---|---|
| 1 | Seattle, WA | 46.9 | 435,146 | 3.8, 7.9, 7.7 | |
| 2 | Colorado Springs, CO | 24.5 | 69,380 | 4.4, 7.5, 8.7 | |
| 3 | San Diego, CA | 25.8 | 299,246 | 3.8, 6.8, 4.9 | |
| 4 | Eugene, OR | 28.9 | 46,099 | 3.9, 5.7, 8.4 | |
| 5 | Buffalo, NY | 12.6 | 51,496 | 5.0, 5.7, 7.7 | |
| 6 | Eureka, CA | 63.4 | 34,795 | 4.5, 4.3, 5.0 | forecast flat, observed rose |
| 7 | Reno, NV | 11.9 | 23,290 | 3.8, 8.9, 12.1 | |
| 8 | Ukiah, CA | 43.5 | 15,038 | 4.7, 7.7, 12.9 | 2nd-highest gap per household |

Dropped by the filter: Los Angeles (observed 2.9 vs baseline 4.4), Rochester (2.0 vs 3.8), Cleveland (3.1 vs 5.2) and Detroit (2.1 vs 4.7). The README should state the filter and list these four, so a reader can see the selection was not tuned.

---

## 3. The need layer (already in the repo)

| Input | Source | In repo? | Confidence |
|---|---|---|---|
| Share without AC (+ margin of error) | Census LACE 2023 (experimental) | yes (`no_ac_pct`, `no_ac_pct_moe`) | B: survey-based, experimental product. *Check the MOE units: 0.1 looks like a proportion, not points.* |
| Heat days: baseline, forecast, observed | Our forecast (data up to 2018) + NOAA | yes | B: rank correlation of forecast vs observed across cities is 0.51 |
| Poverty, living alone, age 65+ | CDC/ATSDR Heat & Health Index 2024 | yes | A |

**Need score** = `gap_per_household` x (1 + vulnerability index). The vulnerability index is the mean z-score of poverty, living alone and 65+ across the 8 cities. The score orders the cities on the dashboard. It does not select them.

---

## 4. The three tests

### A. Homes: can the wiring take it?

| Input | Source | Unit | Confidence |
|---|---|---|---|
| Homes built before 1980 (likely 60-100 A panels) | ACS B25034, county | % | A for the count, **C as a proxy for panel size** |
| Renter-occupied share | ACS B25003 | % | A |
| Electric-resistance or oil heating share | ACS B25040 | % | A |
| Multi-unit share (window/portable vs ductless) | ACS B25024 | % | A |
| Cost of a service upgrade | Literature range ($2k-$6k) | $ | C |

- **Output:** estimated homes needing a panel upgrade = households without AC x pre-1980 share x P(undersized panel | pre-1980). That probability is an assumed range, for example 0.4-0.7.
- **Verdict:** a city is "strained" when upgrades exceed 30% of homes without AC.
- **Link to bills:** the electric-heating share is the heat-pump swap opportunity, so it also feeds test C.

### B. Grid: can the summer peak take it?

| Input | Source | Unit | Confidence |
|---|---|---|---|
| City to utility to balancing authority | HIFLD Electric Retail Service Territories + EIA-861 BA sheet | mapping | A (B where a county has several utilities) |
| Observed summer peak, 2019-2025 | EIA-930 hourly demand by BA | MW | A (analysis only, never a forecast input) |
| Summer vs winter peaking | EIA-930 | label | A |
| Reliability risk for the area | NERC Summer Reliability Assessment 2025 | normal / elevated / high | B (qualitative) |
| kW per added unit | Literature: room unit 0.5-1.2, mini-split 0.8-1.5 | kW | C |
| Adoption if the program runs | Scenario slider: 25 / 50 / 100% | % | scenario, not estimated |
| Coincidence at peak | 0.6-0.9 | ratio | C |

- **Output:** added peak = households without AC x adoption x kW x coincidence. Show it as % of the observed summer peak and % of the summer-winter gap (headroom for winter peakers).
- **Verdict:** "holds" below 3% of peak, or within headroom; "strained" at 3-8%, or when NERC rates the area elevated; "fails" above 8%, or when NERC rates it high. These cut-offs go in `config.json` before any results.

### C. Bills: can households pay for it?

| Input | Source | Unit | Confidence |
|---|---|---|---|
| Residential price, by utility | EIA-861 (latest year) | ¢/kWh | A |
| Time-of-use or summer rate | Utility tariff sheets (by hand for 8 cities) | ¢/kWh | A where found |
| Cooling kWh per season | cdd (forecast) x kWh per cdd per unit | kWh | B for cdd, C for the factor |
| Low-income energy burden today | DOE LEAD tool | % of income | B |
| Heating savings from a heat pump replacing resistance or oil | Literature COP 2.5-3 vs 1 | $/yr | C |

- **Output:** added summer bill for a low-income household, then net annual change once the heat-pump heating savings are counted.
- **Verdict:** "fails" when the energy burden goes above 6% (the common affordability line).

### Optional D. Carbon (supports "why it is sustainable")

Add grid emissions (lb CO2 per MWh, EPA eGRID subregion) x added MWh. Confidence A.

---

## 5. How confidence works

Every input carries one of three grades, shown as a badge:

| Grade | Meaning | Examples | How it enters the model |
|---|---|---|---|
| **A** | Measured, published | EIA prices, EIA-930 peaks, ACS counts | point value (or ACS MOE) |
| **B** | Measured with real error, or our forecast | LACE no-AC %, forecast heat days, NERC rating | value ± its error (MOE, backtest MAE) |
| **C** | Assumed from literature | kW per unit, panel probability, kWh per cdd | uniform range |

**Propagation:** run a Monte Carlo with 2,000 draws over every B and C range. For each city and test, report:

- the median and the 10-90% band of the output;
- the share of draws that give each verdict. A cell is labelled with a verdict only when at least 80% of draws agree. Otherwise it reads **"uncertain"** and names the input that drives the spread (largest rank correlation with the output).
- rank stability: how often a city stays in the top 8 when the need inputs vary.

As a result, the dashboard's lowest-confidence cells point to the next data to collect.

---

## 6. Dashboard layout

1. **Header:** the question, the 8 cities, and the adoption slider (25 / 50 / 100%).
2. **Matrix (main view):** cities in rows, sorted by need; columns are Need, Homes, Grid, Bills (and Carbon). Fill colour shows the verdict; a hatched cell is "uncertain"; each cell carries an A/B/C badge.
3. **City card (on click):** heat days (baseline, forecast, observed), the three outputs with their bands, the inputs with sources, and the main driver of uncertainty.
4. **Comparison charts:** added peak as % of the summer peak (bar with 10-90% whiskers); net bill change for a low-income household.
5. **Method and limits:** data rule note, assumptions table, sources.

Build it from the Dashboard artifact type, with the data in a JSON file produced by the script below.

---

## 7. Build steps

1. Fix `config.json`: the selection rule, verdict cut-offs and assumption ranges, before any results.
2. `code/policy_grid_inputs.py` downloads EIA-861, EIA-930 (2019-2025 summer peaks), the HIFLD territories and ACS B25034/B25040/B25024/B25003, then caches them to `data/policy_grid/`.
3. Collect by hand, for 8 cities: the NERC area rating and summer tariff. Each gets a source row in `data/policy_sources.md`.
4. `code/policy_cooling_readiness.py` runs the selection, tests A-C, the Monte Carlo and the verdicts, and writes `outputs/cooling_readiness/{cities.json, summary.md}`.
5. Build the dashboard from `cities.json`.
6. Update the README Policy Idea and data card (new external sources).

**Data rule:** EIA-930 demand and NOAA observations from 2019-2025 respond to the weather. They are used for analysis only, never as a forecast input, as with the existing policy analysis.

## 8. Open decisions

- ~~Keep or replace LA and Rochester?~~ Decided: filter them out; Reno and Ukiah are in.
- 8 cities, or fewer?
- Default adoption scenario: 50%?
- Include carbon (D)?
