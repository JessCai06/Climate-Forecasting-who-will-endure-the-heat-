# Policy Idea: research essay outline

**Working title:** [Planning on yesterday's weather: grid reserves, electricity bills and livable homes as U.S. summers warm]

**Status:** sections 1-5 drafted with sources and code. Revised 2026-11-09 after a review of contradictions: national focus (Texas kept as a case study), the question reframed around the gap between plans built on past weather and the forecast, household use corrected by household size, the price channel downgraded to a scenario, hot nights carried into the grid result, and livability split into "no AC" and "can't afford to run AC". Every `[ ]` is still a blank.

**Data rule:** forecasts of temperature, precipitation, hottest day and cdd use only data up to 2018-12-31. Section 5 projects electricity demand and prices from data up to 2018 plus our weather forecast. Observed 2019-2025 electricity data is used only to check those projections, never as an input.

---

## The line of reasoning in one view

```
0. Question
   Grids and household budgets are planned on past weather. As U.S. summers warm, does that leave
   grids short and low-income households unable to afford, or go without, the cooling that keeps homes livable?
        |
1. Define the bar
   Affordable = electricity at most 6% of a poverty-line income x the state's electricity share of home energy
                (about 4.4% nationally: $370-696/yr for 1 person, $765-1,439 for 4, by state, 2018 dollars)
   Livable    = indoors at or below 82 F; a day with a high >= 95 F requires cooling (fans stop
                protecting); a night with a low >= 75 F gives no relief
        |
2. The weather that is coming      cooling-required days +21%, hot nights +48%, cdd +19% (our forecast)
3. The grid as it has been         +2% peak demand per F of daily high; +1.5% overnight floor per F of low
4. Prices as they have been        hot years did not raise prices; low-income bills were already over
                                   the bar in 45 of 46 states (1 person) and 36 (family of 4)
        |
5. 2019-2025: plan vs forecast     warming uses ~1/5 of the reserve cushion (ERCOT short in a hot summer);
                                   bills +$17-33/yr; livability fails as "no AC" (North/West) or
                                   "AC too costly to run / power out" (South)
        |
6. Policy                          plan on forecast weather; cut low-income peak use; protect bills in heat;
                                   cooling where there is none
        |
7. Limits: cold-side risk, the 50/50 assumption, household-size data, humidity
```

Each section answers one question, gives one finding, and hands one thing to the next section.

---

## 0. Introduction and question

- **Hook:** [one event up to 2018 where heat, grid strain and bills met: e.g. Texas, August 2011, record peaks on 15 days, an emergency alert and 1,500 MW of demand cut]
- **The question:** grid operators plan capacity on a 50/50 peak forecast built from past weather, and households budget on past bills. As the summers we forecast for 2019-2025 arrive, does that leave grids short, and low-income households unable to afford, or forced to go without, the cooling that keeps homes livable?
- **What the essay argues (to state up front):**
  - Low-income electricity bills were already over an affordable share of income in almost every state before any warming.
  - The forecast heat adds little to those bills.
  - It matters most on the grid: it quietly uses up the reserve cushion where plans were already thin.
  - It splits livability into two problems: no AC in the North and West, and AC too costly to run (or without power) in the South.
- **Why it matters:** cooling is the response to heat. It needs electricity, and the people least able to pay are also the most exposed.
- **Roadmap:** define the bar (1), then show weather (2), grid (3) and prices (4), set the forecast against the plan (5), and propose policy (6).
- **Hands to 1:** the need for a measurable definition of "affordable" and "livable".

## 1. Defining the bar: affordable and livable

### 1a. Affordable (drafted 2026-11-09)

- **Question:** how much can a household at the poverty line pay for electricity before it is unaffordable?
- **Measure:** energy burden, meaning home energy spending ÷ household income.
- **Threshold:** above **6%** of income is a high burden and above **10%** is severe. These cutoffs have been standard for decades (APPRISE 2005, used by ACEEE and DOE). The 6% comes from two rules of thumb: housing should cost at most 30% of income, and energy is about 20% of housing costs (30% × 20% = 6%; Fisher, Sheehan & Colton, 2003). New York's utility regulator adopted 6% as policy in 2016, and other states use it in affordability programs.
- **From all home energy to electricity:** the 6% covers every home fuel. Electricity was **73%** of U.S. household energy spending in 2020 ($170.5 billion of $232.8 billion; EIA RECS 2020). So the electricity share of the bar is 6% × 0.73 ≈ **4.4% of income**. This varies by state (electricity is 94% of home energy use in Florida and 29% in Illinois), so section 4 should use each state's own share from the RECS state tables.
- **Poverty line:** HHS poverty guidelines, 48 contiguous states and D.C. These are what assistance programs use; Census poverty thresholds are the statistical measure. 2018: **$12,140** for one person, **$25,100** for four. 2025: **$15,650** and **$32,150**.
- **The bar in dollars:**

| Household at the poverty line | All home energy, 6% | Electricity share (× 0.73) | Severe, 10% |
|---|---|---|---|
| 1 person, 2018 | $728 a year ($61 a month) | **$533 a year ($44 a month)** | $1,214 a year |
| 4 people, 2018 | $1,506 a year ($126 a month) | **$1,103 a year ($92 a month)** | $2,510 a year |
| 1 person, 2025 | $939 a year ($78 a month) | **$688 a year ($57 a month)** | $1,565 a year |
| 4 people, 2025 | $1,929 a year ($161 a month) | **$1,413 a year ($118 a month)** | $3,215 a year |

- **The bar is already crossed before any new heat:**
  - The average U.S. household that uses electricity spent **$1,380** on it in 2020 (RECS 2020). That is above the electricity bar for a four-person poverty-line household in 2020 (about $1,151, using the 2020 guideline of $26,200; the guideline is to verify).
  - Households below 200% of the poverty line spent a median **8.1%** of income on home energy, against **2.3%** for everyone else (ACEEE 2020, 2017 data).
  - So the question for section 5 is how much hotter summers push bills further over the bar, not whether they cross it.
- **Which year's dollars (decided 2026-11-09): 2018 dollars.** The bar is fixed at the 2018 guideline: $533 a year for one person and $1,103 for four. 2018 is the last year our forecasts may use, so the whole essay stands at the end of 2018. Every bill and price in sections 4 and 5, historical or projected, is converted to 2018 dollars with the BLS consumer price index (CPI-U, annual average). The 2025 rows above are for reference only, to show the bar's size in today's money.
- **Which household:** report both sizes. The one-person household matters most for heat, because people living alone, often older, are among the most at risk in heat waves. **[source for heat risk and living alone / age: CDC, heat-dome death reviews]**
- **Who gets help today:** LIHEAP, the federal home energy assistance program, lets states set income limits between 110% of the poverty guideline and the greater of 150% of the guideline or 60% of state median income (ACF). Most of its money goes to heating; how much goes to summer cooling is **[ ]**.
- **Revised 2026-11-09: three corrections to how the bar is used.**
  1. **The bar is state-specific:** 6% × that state's electricity share of home energy spending (RECS 2020; 51% in Maine to 96% in Florida), not the national 73%. Section 4 has the table.
  2. **Use matches the household:** a single person's bill uses what low-income single-person households use, and a family's uses what families use (RECS 2015 microdata, section 4c). The earlier draft gave both the all-household average.
  3. **The bar is a benchmark, not a spending limit.** Real households pay more than 6%, fall behind on bills, or are disconnected. So the essay reports "the share of income needed to keep the power and cooling on", and treats bill arrears and shut-offs as the real-world harm (section 6).
- **Hands to 4 and 5:** an electricity bar of **6% × the state's electricity share** of a poverty-line income (national median about $528 for one person and $1,092 for four, 2018 dollars), plus a severe line at 10%.

### 1b. Livable (drafted 2026-11-09)

- **Question:** what is the highest temperature a person can survive or safely live in, and when does staying livable require electricity?
- **Three kinds of limit, from survival down to everyday safety:**

| Kind | Limit | Source | What it means |
|---|---|---|---|
| Survival, in theory | Wet-bulb 35 °C (95 °F at 100% humidity) | Sherwood & Huber 2010 | Above this for hours, the body cannot shed heat even at rest in shade. Based on theory, not measurements in people. |
| Survival, measured, young adults | Wet-bulb 30-31 °C in humid heat; 25-28 °C in dry heat | Vecellio et al. 2022 (J. Appl. Physiol.) | No subject reached 35 °C. The limit depends on humidity, so no single wet-bulb number works everywhere. |
| Survival, modeled, older adults | Wet-bulb about 22-34 °C, versus 26-34 °C for young adults | Vanos et al. 2023 (Nature Communications) | Older people sweat less, so their limit is up to 13 °C below 35 °C, lowest for older women in dry heat. Age lowers safe limits more than warming does. |
| Fans stop protecting | Air above about 90-95 °F (32-35 °C) | CDC (archived: fans don't prevent illness "in the high 90s"; recent reports cite 90 °F, to verify on cdc.gov); WHO (about 35 °C) | Above this a fan can raise body temperature. Only real cooling helps. |
| Healthy indoor range | 18-24 °C (64-75 °F); no demonstrated risk for healthy people at rest | WHO Housing and Health Guidelines 2018 | Evidence on harm above 24 °C is rated low certainty. The widely quoted "32 °C by day" figure is not in the WHO text (to verify). |
| Legal indoor maximums in U.S. rentals | 80 °F (Montgomery County, MD, 2020); 82 °F with AC, 86 °F with evaporative coolers (Phoenix); 82 °F (LA County, unincorporated, from 2027) | Local codes, via news reports (`data/policy_rules.csv`) | Governments have already written a livable indoor line, and it sits around 80-82 °F. |

- **Definition to adopt (two lines, both measurable with our data):**
  1. **Indoors, livable means at or below 82 °F.** This is the most common U.S. legal maximum, and it sits below the fan limit. It is the standard that cooling has to meet.
  2. **Outdoors, a "cooling-required day" is a day with a high of 95 °F (35 °C) or more.** Above this, fans no longer protect and homes without cooling go past the indoor line, so electricity for cooling becomes a need rather than a comfort. A **hot night** (low of 75 °F, 24 °C, or more) is counted too, because the home cannot cool down overnight. These are our own thresholds, built from the limits in the table, and the essay should say so.
- **Why not wet-bulb:** our data has daily highs and lows but no humidity, so it cannot measure wet-bulb temperature. The dry-bulb lines above are conservative for older adults, whose limits Vanos et al. found far below 35 °C wet-bulb. They understate risk in humid places, where the same air temperature is more dangerous. Section 7 should name this limit. **[optional: add humidity from a station dataset for a few humid cities as a check]**
- **Why the vulnerable matter most:** older adults and people with low sweat capacity reach their limits first (Vanos et al. 2023), and they are also more likely to live alone and on low incomes. **[source linking age, living alone and heat deaths: CDC, heat-dome reviews]**
- **How 1a and 1b connect:** on a cooling-required day, a household either runs cooling and pays (pressure on the affordability bar) or skips it and goes past the livable line. The essay's central tension is a household forced to choose between the two bars.
- **Revised 2026-11-09: livability fails in two different ways, and the essay treats them separately.**
  1. **No AC to turn on.** Census LACE 2023 puts homes without AC at 13-33% in much of the North and West: Washington 33%, Maine 24%, Montana 24%, Oregon 18%, California 17%. The fan limit (95 °F) and the 82 °F indoor line apply directly.
  2. **AC that is too costly to run, or without power.** In the South, 98-99.5% of homes have AC. The risk is a household turning it down or off to keep the bill payable, or losing power when the grid runs short. Here the livability line is crossed through the bill (1a) or the grid (section 5), not through missing equipment.
- **Hands to 2:** two counts per city and year, cooling-required days (high ≥ 95 °F) and hot nights (low ≥ 75 °F), plus the 82 °F indoor standard used in sections 5 and 6.

## 2. The forecast weather

(Drafted 2026-11-09. Code: `code/policy_grid_heat_days.py`. Output: `outputs/grid_heat_days/summary.md`, `city_heat_days.csv`. 197 cities with enough data.)

- **Question:** how much hotter will 2019-2025 be than the climate the grid was built for (1976-2005)?
- **Method:** forecasts use data up to 2018 only.
  - Cooling degree days and hottest day come from our submitted forecast (Experiment 5B).
  - Cooling-required days and hot nights use the same delta method: the city's real daily highs and lows from its last 10 years up to 2018, warmed by the shared warming rate (highs +0.048 °F a year, lows +0.057 °F a year).
- **Evidence (median city, and totals across the 197 cities):**

| Measure | 1976-2005 | Forecast 2019-2025 | Change |
|---|---|---|---|
| Cooling degree days (median city) | 1,032 | 1,252 | **+19%**; rises in 193 of 197 cities |
| Cooling-required days, high >= 95 °F (all cities, per year) | 3,208 | 3,884 | **+21%** |
| Hot nights, low >= 75 °F (all cities, per year) | 2,105 | 3,122 | **+48%** |
| Cities with a month or more (30+) of cooling-required days | 31 | 44 | +13 cities |
| Cities with at least one hot night a year | 106 | 119 | +13 cities |
| Hottest day of the year (median city) | 98.3 °F | 98.4 °F | about flat |

- **Three patterns the essay should draw out:**
  1. **Nights warm faster than days.** Hot nights rise by about half; cooling-required days by a fifth. With no relief overnight, homes stay hot, people stay at risk (1b), and cooling runs around the clock, which raises demand and bills (sections 3-5).
  2. **The rise is regional, not everywhere.** The median city's cooling-required days barely change (9.1 to 8.9), because most of the increase lands in places that are already hot:
     - Texas: 448 to 611 days across its 10 cities, and hot nights 446 to 681.
     - The Gulf Coast: Louisiana, Mississippi, Alabama, and Florida's nights (621 to 846).
     - The Southwest and California: New Mexico, Nevada, Arizona's nights, and the Central Valley.
     - Northern Plains cities (the Dakotas) see fewer 95 °F days than in 1976-2005, though their cdd still rises.
  3. **Cooling demand grows everywhere, even where extremes don't.** Cooling degree days rise in 193 of 197 cities. Cooler northern cities have the largest percentage gains: Washington +55% and Nevada +63% (median of their cities). There, homes were often built without AC.
- **Places to follow into sections 3-5:**
  - Austin (57 to 84 cooling-required days), San Antonio, Corpus Christi and Houston in Texas, a state on its own grid (ERCOT), which is an advantage for the grid analysis.
  - Tampa, West Palm Beach and Miami for hot nights (Miami 124 to 152 a year).
  - Fresno and Bakersfield, California (about 89 and 86 days).
  - Roswell, New Mexico.
- **How sure:**
  - Across cities, the forecast ranks cities almost exactly as observed 2019-2025 did: rank correlation 0.97 for both hot days and hot nights (analysis only, never a forecast input).
  - The forecast is, if anything, **conservative**. The observed median was 10.9 cooling-required days and 2.2 hot nights, against our forecast of 8.9 and 2.0. In Austin we forecast 84 days and 98 were observed.
  - Held-back forecast error for cdd from the submission experiments: **[add from outputs/exp05b]**.
- **Limits:**
  - Airport stations understate heat in city centres.
  - Dry-bulb lines understate humid risk.
  - The delta method shifts temperatures but does not reshape heat waves.
- **Finding:** by 2019-2025, the forecast adds about a fifth more cooling-required days and half again as many hot nights across U.S. cities. The increase is concentrated in Texas, the Gulf Coast and the Southwest, and nights warm faster than days.
- **Hands to 3 and 5:** per-city forecast cdd, cooling-required days and hot nights (`outputs/grid_heat_days/city_heat_days.csv`), and a short list of regions where demand and livability pressure grow most: Texas/ERCOT, the Gulf Coast, the Southwest and California.

## 3. The grid as it has been: how much heat moves demand

(Revised 2026-11-09, national. Code: `code/policy_grid_demand.py`. Output: `outputs/grid_national/summary.md`, `sensitivity.csv`. Data: EIA-930 hourly demand for every balancing authority, July 2015 - December 2018, in EIA's 13 regions; challenge daily temperatures, cities weighted by county households. Long-run check: ERCOT 2002-2018, `code/policy_grid_ercot.py`.)

- **Question:** how much does a hotter day push electricity demand up, region by region, once growth is held fixed?
- **3a. The national link:** across the contiguous U.S., each 1 °F on the household-weighted daily high adds **about 13,700 MW to the daily peak, 2.2% per °F** (412 summer days, R² 0.88).
- **3b. By region (summer days, growth held fixed by year):**

| Region | Peak: % per °F | Night floor: % per °F | Fit (day) |
|---|---|---|---|
| Florida | **3.4%** | 3.0% | 0.84 |
| California | 2.1% | 1.5% | 0.76 |
| Mid-Atlantic (PJM) | 2.0% | 1.4% | 0.83 |
| Texas (ERCOT) | 2.0% | 2.1% | 0.95 |
| Tennessee, Carolinas, New York | 1.9-2.0% | 1.5-1.7% | 0.83-0.93 |
| Midwest (MISO), New England, Central (SPP) | 1.8% | 1.2-1.8% | 0.83-0.91 |
| Southeast | 1.7% | 1.2% | 0.37 (weak) |
| Southwest | 1.4% | 1.0% | 0.44 (weak) |
| Northwest | 1.2% | 0.8% | 0.61 |

  - The median region gains **1.9% of peak per °F** of daily high, and **1.5% of its overnight floor per °F** of daily low. Hot nights raise the floor the grid never gets below, and section 2 found nights warming fastest.
  - **The long record agrees.** ERCOT's own 2002-2018 data (section 3 case study) gives 1.9% per °F, against 2.0% from the short national record.
  - In ERCOT's long record, demand does **not** rise faster per degree above 95 °F (about 1,200 MW per °F below 95 and 1,100 above). Extreme days are dangerous because spare capacity runs out, not because demand accelerates.
- **3c. The cold side of the risk:** four regions (Tennessee, the Carolinas, the Southeast, the Northwest) had their yearly peak in **winter** at least once in 2016-2018. A heat-only essay must say that grid risk runs both ways (section 7).
- **3d. Case study, ERCOT:**
  - Peak demand grew +1.4% a year from 2002 to 2018.
  - 1 °F of heat adds more to the peak than a year of growth.
  - The 2011 heat wave brought emergency alerts and about 1,500 MW of demand cut.
  - Details: `outputs/grid_ercot/summary.md`.
- **Limits:**
  - EIA-930 has only 3.5 summers.
  - Cities are assigned to regions by state.
  - Load is what customers drew, so demand cut in emergencies is not seen.
  - The Southeast and Southwest fits are weak.
- **Finding:** across U.S. grids, a 1 °F hotter day adds about 2% to peak demand (1.2-3.4% by region), and a 1 °F warmer night lifts the overnight floor about 1.5%.
- **Hands to 5:** each region's % per °F (day and night).

## 4. Prices as they have been, and how affordable they were

(Revised 2026-11-09, national. Code: `code/policy_grid_prices_national.py`. Output: `outputs/grid_prices_national/summary.md`, `states.csv`, `recs_low_income.csv`. Data: EIA-861 filings of every utility and retail provider, 2002-2018; BLS CPI-U; RECS 2015 microdata (5,686 homes, replicate weights); RECS 2020 state table. Texas case study: `code/policy_grid_prices.py`.)

- **Question:** what have households paid for electricity, does heat raise the price, and were low-income households under the bar from 1a?
- **4a. Prices and bills (U.S. average, 2018 dollars):**
  - The price was 11.8 ¢/kWh in 2002 and **12.8 ¢ in 2018** (+0.6% a year in real terms).
  - The average customer used about 11,000 kWh a year throughout.
  - The average bill was **$1,410 in 2018**.
- **4b. Heat moves use, not price.** Across 46 states and 17 years, with state and year effects, a hotter year (100 more cooling degree days) changed the real price by **−0.002 ¢/kWh (standard error 0.023)**, which is effectively zero. Price swings were national (natural gas, policy), not local weather. **So the essay cannot claim that heat raises prices from this history.** Any price channel in section 5 is a risk scenario, not a result.
- **4c. What low-income households actually use, by household size (RECS 2015, weighted):**

| Household | Northeast | Midwest | South | West |
|---|---|---|---|---|
| 1 person, income < $20,000: kWh a year (of which cooling) | 4,287 (383) | 6,377 (477) | **8,430 (2,031)** | 5,865 (634) |
| 4 people, income < $40,000 | 7,520 (880) | 9,377 (857) | **14,659 (2,715)** | 9,027 (982) |
| Share with AC (1 person / 4 people) | 70% / 80% | 77% / 83% | 91% / 89% | **66% / 60%** |

  - These are the corrected household figures. The earlier draft gave a single person the all-household Southern average (10,829 kWh), which overstated their use. For a family of four it understated: they use about 14,700 kWh.
  - The RECS income brackets ($20,000 for one person, $40,000 for four) reach about 160% of the poverty line, so these are near-poor households, not only those below the line. RECS 2015 has no poverty flag.
- **4d. The bar is state-specific.** 6% of the 2018 poverty line × electricity's share of that state's home energy spending (RECS 2020): 51% in Maine, 52% in New Hampshire, 85% in Texas, 96% in Florida. For one person that gives $370 (Maine) to $696 (Florida) a year; for four, $765 to $1,439.
- **4e. How affordable it was (2018 prices, 2015 use, 46 states):**
  - **A single low-income person was over the bar in 45 of 46 states** (the median state: 6.8% of a poverty-line income, 1.49 times the bar). **They were over the severe line in 18.**
  - **A family of four was over the bar in 36 of 46** (median 5.3%, 1.21 times the bar).
  - The worst states are high-price ones: New England, New York and California (1.7-1.8 times the bar for four). The South follows, where use is highest (Texas, Florida, Georgia and Alabama, about 1.4 times).
- **Finding:** before any forecast warming, electricity was already unaffordable for low-income households in almost every state. The cause is income, price and baseline use, not heat, and hot years did not raise prices.
- **Hands to 5:** state bars, state 2018 prices, and low-income use by region and household size (with cooling separated out).

## 5. Putting it together: the forecast window, 2019-2025

(Revised 2026-11-09, national. Code: `code/policy_grid_projection_national.py`. Output: `outputs/grid_projection_national/summary.md`, `areas.csv`, `states.csv`. Every input is dated 2018 or earlier. The grid plan is **NERC's 2018 Long-Term Reliability Assessment** (December 2018): each area's Anticipated Reserve Margin and Reference Margin Level, 2019-2025. Texas case study with ERCOT's own plan: `code/policy_grid_projection.py`.)

- **Question:** does planning on past weather leave grids and low-income households exposed as the forecast heat arrives?
- **How the plan treats weather:** NERC's margins rest on each area's **50/50 peak forecast**, a midpoint built from past weather. Weather swings around it are what the Reference Margin Level is meant to cover. Our assumption (stated in section 7): those midpoints do not include warming.
- **Method:**
  1. For each of 14 U.S. NERC areas, take the 15 summers of 2004-2018, each warmed to the target year by the forecast rate (+0.048 °F a year).
  2. The change in the peak-day high × the area's % per °F (section 3) = the added peak.
  3. Margin with weather = (1 + plan margin) ÷ (1 + added peak) − 1.
  4. An average warmed summer is compared with the Reference Margin Level. A **hot summer** (about 1 in 10) is compared with **running short (below 0) or emergency territory (below 5%)**. Comparing a hot summer with the reference level would count the same weather twice.
- **5a. Grid: what warming does to the cushion:**

| NERC area | Plan margin 2019 → 2025 | Reference | 2025 with warming | 2025 in a hot summer |
|---|---|---|---|---|
| ERCOT (Texas) | 11.2% → 5.3% | 13.75% | **3.9%** | **−1.3% (short)** |
| MISO (Midwest) | 21.3% → 15.0% | 17.1% | **13.6%** | 7.0% |
| California | 23.3% → 20.4% | 12.0% | 18.7% | 9.4% |
| SERC-N, SERC-E, Southwest, Rockies, Florida, SPP | 16.6-24.0% in 2025 | 12.0-15.7% | 15.5-22.4% | 10.4-13.6% |
| New York, Northwest, New England, PJM, Southeast | 22.7-33.4% in 2025 | 15.0-19.4% | 21.1-31.6% | 15.4-24.7% |

  - **Warming's effect is about the same size as the plans' own erosion.** By 2025 the median area loses 1.6 points of margin to warming, against 2.3 points from its own plan (growth and retirements). **Warming uses up about a fifth of the cushion** each area planned above its reference level.
  - Warming does not push any new area below its reference level by 2025. Only ERCOT (all 7 years) and MISO (3 years) are below it, and they were below it in the plan already. **But it deepens the shortfall exactly where the cushion is thinnest.**
  - **A hot summer** is about 4 °F on the peak day and 8.4 points of margin (median area). With warming, it leaves ERCOT under 5% spare in 5 of 7 years, and short of capacity in 2025. Every other area keeps at least 7% in a hot summer.
  - **Hot nights:** by 2025 the overnight floor rises 0.6-2.4% (Florida highest). The grid's quietest hours get less quiet, which reduces the time available for maintenance and recovery.
- **5b. Bills for low-income households (2018 dollars, 46 states):**
  - The forecast heat adds **$17 a year for a single person and $33 for a family of four** (median state, against the 1976-2005 climate). The largest increase is Texas, $70 for four.
  - The number of states over the bar does **not** change: 45 for one person and 36 for four, in both climates.
  - Just keeping the cooling on costs a poverty-line single person a median **0.7% of income**, and up to **3.6% in Florida** and 2.8% in Texas.
  - **Scenario, not a forecast:** add the ERCOT 2016-2018 wholesale rise (+1.1 ¢) where a hot summer leaves under 5% spare. That adds one state (Texas's four-person household was already over), because only ERCOT reaches that point. **Through 2025, heat's route to unaffordability runs through usage in the hottest states, and through grid risk in Texas. It does not run through prices nationally.**
- **5c. Livability: two different problems:**
  - **North and West: homes without AC.** In Washington 33% of homes have no AC, in Maine 24%, Montana 24%, Wyoming 18%, Oregon 18%, California 17%, New Hampshire 15%, and Colorado and Nevada 13%. Cooling-required days are rising in several of these (Nevada 22 → 34 a year, Utah 26 → 34, Colorado 12 → 17). For these households livability fails without any grid event, because they have nothing to turn on.
  - **South: AC everywhere, but costly to run, and hot nights rising.** 98-99.5% of homes have AC (LACE). Hot nights rise steeply: Florida 69 → 96, Texas 46 → 75, Louisiana 26 → 46, Mississippi 21 → 40. Low-income households are already over the bar (1.4-1.7 times), so the risk is turning the AC down or off to save money, or losing power when the grid is short (ERCOT).
- **Check against what happened (analysis only, needs a team member's approval):** observed 2019-2025 peaks, emergency events and bills. **[ask before using post-2018 data]**
- **Confidence:**
  - Measured: NERC plans, 2018 prices, RECS use, LACE AC shares.
  - Forecast: warming and cdd. Section 2 found the forecast runs low, so warming effects are probably understated.
  - Assumed: the 50/50 forecasts exclude warming; a linear demand response; the hot summer is the 90th percentile of 15 warmed summers; the scarcity price.
- **Finding:** for 2019-2025, the forecast heat matters most on the grid and least on the bill.
  - It uses up about a fifth of the planned reserve cushion, and that matters where plans were already at or below their reference level (ERCOT, MISO). ERCOT runs short in a hot summer.
  - It adds only $17-33 a year to low-income bills, which were already over the bar in 45 of 46 states.
  - Livability fails in two ways: no AC in the North and West, and AC that is too costly to run or without power in the South.
- **Hands to 6:**
  1. **Planning:** a reserve gap of about 1-2 points by 2025 from warming, and ERCOT short in a hot summer.
  2. **Affordability:** a structural gap in almost every state, a median $284 a year above the bar for a single low-income person (up to $668), which heat barely changes.
  3. **Livability:** households without AC in the North and West, and households in the South who cannot afford to run the AC they have.

## 6. What needs to be done

- **Question:** which policies close the three gaps from section 5 (planning, affordability, livability) without making emissions or costs worse in the long run?
- **Criteria for a good policy:** closes a gap found in 5; is affordable to fund; lowers or does not raise peak demand; works within existing institutions.
- **Candidate levers, matched to the gaps (to evaluate, not decided):**
  1. **Planning gap (grid):** plan reserves on forecast weather, not past weather. NERC and its areas would add a warming adjustment to the 50/50 peak, starting with areas already at or below their reference level (ERCOT, MISO). **[who: NERC, regional operators, state commissions]**
  2. **Affordability gap (structural, almost every state):** income-based rates or discounts, like California's CARE program [source, size], and LIHEAP money for summer cooling, not only winter heating **[share of LIHEAP spent on cooling]**. The gap is roughly $200-670 a year for a single low-income person.
  3. **The lever that serves both:** cut low-income peak use with efficient cooling (heat-pump replacements for old AC and electric resistance heat), weatherization and demand response at peaks. Lower peak demand eases the grid, and lower use eases the bill. **[size: kW and $ saved per home]**
  4. **Livability, North and West:** cooling where there is none, for example cooling-ready rental rules and heat-pump programs (the earlier Seattle idea fits here), plus indoor maximum temperature rules.
  5. **Livability, South:** no disconnections during heat (shut-off moratoria on cooling-required days), and priority restoration and cooling centers for outage risk where reserves are thin.
- **Proposal:** [the one or two levers that best close the gap, who would run them (state commission, utility, city, federal program), and the cost].
- **Why it is sustainable:** [effect on peak demand, emissions and long-run cost].
- **Finding:** [one sentence].

## 7. Limits and next steps

- **The cold side.** Four regions had winter yearly peaks in 2016-2018 (section 3c), and section 2 found extreme cold days falling on average, not disappearing. The essay is about heat, but grid risk runs both ways. Readers will know Texas's largest grid failure in the window came in winter. Using post-2018 events as evidence needs a team member's approval under `code/AGENTS.md`. **[decide how to mention it]**
- **The 50/50 assumption.** Section 5 assumes NERC areas' peak forecasts do not already include warming. If an area's forecast does, our warming effect overstates its gap.
- **Size of the warming effect.** Warming is a modest part of grid risk to 2025 (about 1-2 points of margin). Growth, retirements and ordinary hot summers are larger. The essay should say so plainly, and note that section 2 found the forecast runs low.
- **Price channel.** Hot years did not raise prices in 2002-2018 (section 4b). The scarcity price is a scenario, not a result.
- **Household data.** RECS 2015 income brackets approximate poverty status, and use is regional (four Census regions) with cooling scaled to each state. Some groups are small (30-149 homes).
- **Data limits:**
  - Airport stations.
  - No humidity: dry-bulb thresholds understate humid risk.
  - EIA-930 has only 3.5 summers.
  - Cities are assigned to grids by state.
  - Alaska and Hawaii are left out.
- **Model limits:**
  - A linear demand response.
  - The peak-day temperature stands in for the peak hour.
  - Load is what customers drew.
- **What would change the conclusion:**
  - If 50/50 forecasts already include warming, the planning gap shrinks.
  - If low-income households cut cooling more than average (likely), use and bills are lower but livability is worse.
  - A real check against 2019-2025 outcomes (with approval) could confirm or overturn the grid result.

## 8. Conclusion

- Restate the question, the bar, the gap from 5, and the proposal from 6, in [3-4] sentences.

---

## Data checklist

| Section | Data | Source (candidate) | Years | Status |
|---|---|---|---|---|
| 1a | Poverty line | HHS poverty guidelines ([2018](https://s3.amazonaws.com/public-inspection.federalregister.gov/2018-00814.pdf), [2025](https://govinfo.gov/content/pkg/FR-2025-01-17/pdf/2025-01377.pdf)) | 2018, 2025 | done |
| 1a | Energy-burden threshold (6% / 10%) | [ACEEE](https://www.energy.gov/sites/default/files/2023-05/Attachment%20J%20-%20ACEEE%2C%20How%20High%20are%20Household%20Energy%20Burdens.pdf); origin of the 6% ([Maine ERAC/VEIC](https://www.maine.gov/meopa/sites/maine.gov.meopa/files/inline-files/2024-08-05%20ERAC_VEIC%20Energy%20Burden%20Early%20Findings.pdf), [NH DOE](https://puc.nh.gov/regulatory/Docketbk/2022/22-043/LETTERS-MEMOS-TARIFFS/22-043-2024-10-31-NHDOE-TECH-STMT-COLTON.PDF)) | - | done |
| 1a | Electricity share of home energy spending (73%) | [EIA RECS 2020 state table](https://www.eia.gov/consumption/residential/data/2020/state/pdf/State%20expenditures.pdf) | 2020 | done (national); state shares to pull |
| 1a | Low-income median burden (8.1% vs 2.3%) | [ACEEE 2020](https://www.aceee.org/press-release/2020/09/report-low-income-households-communities-color-face-high-energy-burden) | 2017 data | done |
| 1a | LIHEAP income limits | [ACF IM2025-02](https://acf.gov/ocs/policy-guidance/liheap-im2025-02-federal-poverty-guidelines-and-state-median-income-estimates) | 2025 | done |
| 1a | 2020 poverty guideline ($26,200 for 4) | HHS | 2020 | to verify |
| 4, 5 | Consumer price index to convert bills to 2018 dollars | BLS CPI-U, annual average | up to 2018; 2019-2025 for the check | to pull |
| 1b | Wet-bulb survival limits | [Vecellio et al. 2022](https://pmc.ncbi.nlm.nih.gov/articles/PMC8799385), [Vanos et al. 2023](https://www.nature.com/articles/s41467-023-43121-5.pdf), Sherwood & Huber 2010 (via citing papers) | - | done; read Sherwood & Huber directly |
| 1b | Fan limit | [CDC archived heat guide](https://webarchive.library.unt.edu/web/20130213222246/http://www.bt.cdc.gov/disasters/extremeheat/heat_guide-page-2.asp); 90 °F per [news reports](https://www.nbcdfw.com/news/national-international/extreme-heat-wave-indoor-fan-temperature/4044586/) | - | verify current CDC page |
| 1b | WHO indoor range 18-24 °C | [WHO Housing and Health Guidelines 2018](https://www.ncbi.nlm.nih.gov/books/NBK535285/) | 2018 | done; "32 °C day" not found in primary text |
| 1b | Rental indoor maximums | [Montgomery County](https://bethesdamagazine.com/2020/02/26/bill-requiring-air-conditioning-at-montgomery-rental-units-approved/), [Phoenix](https://www.multifamilydive.com/news/tenant-right-cooling-laws-cities-extreme-heat-indoor-maximum-temperature/725113/), `data/policy_rules.csv` | 2020-2025 | done; check municipal codes |
| 2 | Cooling-required days (high >= 95 F), hot nights (low >= 75 F) | Challenge daily data + our forecast (`code/policy_grid_heat_days.py`) | baseline, 2019-2025 | done |
| 2 | cdd, hottest day forecast | Our submission (Exp. 5B) | 2019-2025 | in repo |
| 3 | ERCOT hourly load by weather zone | [ERCOT load archives](https://www.ercot.com/gridinfo/load/load_hist) (`code/policy_grid_ercot.py`) | 2002-2018 | done |
| 3 | ERCOT reserve margins (13.75% target; 8.1% for summer 2019) | [ERCOT CDR Dec 2018](https://www.ercot.com/files/docs/2018/12/04/CapacityDemandandReservesReport-Dec2018.pdf), [Utility Dive](https://www.utilitydive.com/news/texas-grid-to-face-tighter-electricity-reserves-this-summer-does-that-sca/543579/), [POWER](https://www.powermag.com/reserve-margins-in-texas-barely-healthy-again-ercot-says/) | 2010-2019 | done |
| 3 | 2011 heat wave emergency | [EIA Today in Energy](https://www.eia.gov/todayinenergy/detail.php?id=7010), [ERCOT EEA report](https://www.ercot.com/files/docs/2011/08/26/05._ercot_operations_report_eea_events_080211_080511_public.doc) | 2011 | done |
| 3 | ERCOT generation mix 2018 | [UT Energy Institute](https://energy.utexas.edu/news/electricity-generated-wind-estimated-overtake-coal-ercot-2019), [EIA](https://www.eia.gov/todayinenergy/detail.php?id=39772) | 2018 | done |
| 3 | National generation and NERC regions | EIA Electric Power Annual, NERC | up to 2018 | to add |
| 4 | Texas residential revenue, sales, customers | [EIA-861 annual files](https://www.eia.gov/electricity/data/eia861/) (`code/policy_grid_prices.py`) | 2002-2018 | done |
| 4 | CPI-U (2018 dollars) | BLS series CUUR0000SA0 (API) | 2002-2018 | done |
| 4 | Electricity share of Texas home energy (85%) | [RECS 2020 state table](https://www.eia.gov/consumption/residential/data/2020/state/pdf/State%20expenditures.pdf) | 2020 | done |
| 4 | Low-income use, South (10,829 kWh; 2,460 for cooling) | [RECS 2015 CE4.9](https://www.eia.gov/consumption/residential/data/2015/c&e/pdf/ce4.9.pdf) | 2015 | done |
| 4 | Houston low-income energy burden (7.1%) | [ACEEE Houston](https://www.aceee.org/sites/default/files/pdfs/aceee-01_energy_burden_-_houston.pdf) | 2020 | done |
| 4 | ERCOT wholesale prices 2016-2018 | [Potomac Economics 2018 State of the Market](https://www.potomaceconomics.com/wp-content/uploads/2019/06/2018-State-of-the-Market-Report.pdf), [IMM report](https://www.ercot.com/files/docs/2019/02/05/11_Independent_Market_Monitor__IMM__Report.pdf) | 2016-2018 | done; confirm in final report |
| 4 | ERCOT offer cap, retail pass-through | PUCT, IMM | - | to find |
| 5 | ERCOT plan: peak (normal weather), firm load, capacity 2019-2023 | [ERCOT CDR Dec 2018](https://www.ercot.com/files/docs/2018/12/04/CapacityDemandandReservesReport-Dec2018.pdf), summer summary | Dec 2018 | done |
| 5 | Projection (`code/policy_grid_projection.py`) | sections 2-4 outputs | 2019-2025 | done |
| 5 | Check data (analysis only) | ERCOT / EIA 2019-2025 | 2019-2025 | needs team approval |
| 3 (national) | Hourly demand, all balancing authorities, 13 regions | [EIA-930 six-month files](https://www.eia.gov/electricity/gridmonitor/about) (`code/policy_grid_demand.py`) | Jul 2015-2018 | done |
| 4 (national) | Residential revenue, sales, customers, every state | EIA-861 annual files (`code/policy_grid_prices_national.py`) | 2002-2018 | done |
| 4 (national) | Low-income use by household size and region | [RECS 2015 microdata](https://www.eia.gov/consumption/residential/data/2015/index.php?view=microdata) | 2015 | done |
| 4 (national) | Electricity share of home energy, every state | [RECS 2020 state table](https://www.eia.gov/consumption/residential/data/2020/state/pdf/State%20expenditures.pdf) | 2020 | done |
| 5 (national) | Anticipated and reference reserve margins, 2019-2028 | [NERC 2018 Long-Term Reliability Assessment](https://www.nerc.com/pa/RAPA/ra/Reliability%20Assessments%20DL/NERC_LTRA_2018_12202018.pdf), Tables 3.1-3.2 (`code/policy_grid_projection_national.py`) | Dec 2018 | done |
| 5 (national) | Homes without AC by county | Census LACE 2023 (via `outputs/cooling_gap/`) | 2023 | done |
| 6 | Low-income rate programs (e.g. CARE), LIHEAP cooling share, efficiency savings | CPUC, ACF, DOE | - | to find |
