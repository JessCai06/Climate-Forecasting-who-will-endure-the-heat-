# Section 2: the forecast weather against the livability line

Cities: 197. Cooling-required day = high >= 95 F; hot night = low >= 75 F. Baseline 1976-2005; forecast 2019-2025 from data up to 2018 (shared slopes: Tmax 0.0484 F/yr, Tmin 0.0571 F/yr; cdd and hottest day from submission.csv). Observed 2019-2025 is NOAA data used as a check only.

## All cities

| Measure | Baseline (median city) | Forecast (median city) | Observed (median city) | Total across cities: baseline -> forecast |
|---|---|---|---|---|
| Cooling-required days per year | 9.1 | 8.9 | 10.9 | 3,208 -> 3,884 |
| Hot nights per year | 1.3 | 2.0 | 2.2 | 2,105 -> 3,122 |
| Cooling degree days | 1,032 | 1,252 | - | median change +19% |
| Hottest day of the year (F) | 98.3 | 98.4 | - | |

- Cities with at least one cooling-required day a year: baseline 170, forecast 170.
- Cities with at least 30 (a month of them): baseline 31, forecast 44.
- Cities with at least one hot night a year: baseline 106, forecast 119.
- Cities where cooling-required days rise: 135; hot nights rise: 135; cdd rise: 193.
- Check (analysis only): rank correlation of forecast vs observed across cities: cooling-required days 0.97 (196 cities), hot nights 0.97 (196 cities).

## By state (sum over the challenge cities in each state, days per year)

| State | Cities | Cooling-required days: baseline -> forecast | Hot nights: baseline -> forecast | cdd change (median) |
|---|---|---|---|---|
| TX | 10.0 | 448 -> 611 | 446 -> 681 | +18% |
| CA | 10.0 | 461 -> 520 | 124 -> 154 | +14% |
| LA | 5.0 | 136 -> 189 | 129 -> 231 | +16% |
| NM | 3.0 | 86 -> 125 | 1 -> 2 | +20% |
| AL | 4.0 | 71 -> 109 | 38 -> 78 | +19% |
| GA | 6.0 | 129 -> 165 | 57 -> 84 | +16% |
| FL | 10.0 | 115 -> 145 | 621 -> 846 | +12% |
| MS | 4.0 | 84 -> 113 | 61 -> 124 | +15% |
| NV | 4.0 | 73 -> 102 | 0 -> 0 | +63% |
| AR | 5.0 | 135 -> 158 | 60 -> 105 | +14% |
| CO | 4.0 | 78 -> 101 | 0 -> 1 | +26% |
| OK | 3.0 | 108 -> 128 | 57 -> 75 | +15% |
| ID | 2.0 | 44 -> 62 | 1 -> 1 | +37% |
| TN | 3.0 | 48 -> 66 | 41 -> 60 | +19% |
| SC | 2.0 | 36 -> 54 | 9 -> 32 | +27% |
| MO | 5.0 | 62 -> 76 | 37 -> 60 | +19% |
| OR | 6.0 | 34 -> 46 | 0 -> 0 | +40% |
| AZ | 4.0 | 403 -> 415 | 228 -> 271 | +14% |
| NC | 4.0 | 23 -> 34 | 37 -> 62 | +24% |
| WA | 5.0 | 39 -> 49 | 0 -> 0 | +55% |
| KS | 4.0 | 105 -> 115 | 19 -> 24 | +13% |
| UT | 1.0 | 26 -> 34 | 1 -> 6 | +29% |
| MT | 5.0 | 37 -> 45 | 0 -> 0 | +19% |
| VA | 4.0 | 39 -> 42 | 36 -> 59 | +21% |
| IN | 4.0 | 18 -> 21 | 10 -> 14 | +19% |
| NJ | 1.0 | 4 -> 7 | 1 -> 2 | +32% |
| WY | 2.0 | 6 -> 8 | 0 -> 0 | +26% |
| MI | 7.0 | 7 -> 8 | 2 -> 8 | +33% |
| DE | 1.0 | 4 -> 6 | 3 -> 6 | +23% |
| KY | 2.0 | 12 -> 13 | 7 -> 18 | +24% |
| MA | 3.0 | 4 -> 5 | 2 -> 4 | +35% |
| NH | 1.0 | 2 -> 3 | 0 -> 0 | +29% |
| VT | 1.0 | 1 -> 2 | 0 -> 1 | +44% |
| NE | 9.0 | 155 -> 156 | 15 -> 21 | +11% |
| MD | 1.0 | 9 -> 10 | 3 -> 5 | +19% |
| OH | 6.0 | 14 -> 14 | 4 -> 10 | +22% |
| PA | 5.0 | 15 -> 15 | 10 -> 19 | +31% |
| ME | 1.0 | 1 -> 1 | 0 -> 0 | +37% |
| NY | 5.0 | 7 -> 6 | 9 -> 14 | +29% |
| IA | 5.0 | 20 -> 20 | 8 -> 10 | +7% |
| MN | 5.0 | 7 -> 6 | 2 -> 4 | +24% |
| IL | 5.0 | 25 -> 23 | 12 -> 17 | +23% |
| WI | 7.0 | 14 -> 12 | 5 -> 6 | +18% |
| WV | 5.0 | 8 -> 6 | 1 -> 2 | +32% |
| ND | 4.0 | 24 -> 17 | 1 -> 0 | +12% |
| SD | 4.0 | 34 -> 23 | 4 -> 6 | +7% |

## Largest rise in cooling-required days per year

| City | State | Baseline | Forecast | Observed (check) | cdd baseline -> forecast |
|---|---|---|---|---|---|
| Austin | TX | 57.0 | 83.7 | 98.1 | 3,045 -> 3,593 |
| CorpusChristi | TX | 36.6 | 62.5 | 69.3 | 3,495 -> 4,037 |
| Roswell | NM | 52.9 | 74.9 | 89.7 | 1,886 -> 2,196 |
| SanAntonio | TX | 54.7 | 75.4 | 88.6 | 3,085 -> 3,565 |
| Shreveport | LA | 35.7 | 54.1 | 58.9 | 2,459 -> 2,945 |
| Tallahassee | FL | 24.6 | 42.9 | 39.6 | 2,552 -> 3,075 |
| Abilene | TX | 50.7 | 68.2 | 81.1 | 2,431 -> 2,821 |
| Montgomery | AL | 23.9 | 41.0 | 36.4 | 2,280 -> 2,713 |
| Fresno | CA | 72.3 | 89.2 | 87.4 | 2,061 -> 2,497 |
| Clayton | NM | 9.5 | 25.4 | 23.3 | 865 -> 1,232 |
| Houston | TX | 41.4 | 57.3 | 70.3 | 2,974 -> 3,494 |
| Bakersfield | CA | 70.5 | 86.2 | 86.9 | 2,263 -> 2,682 |
| Amarillo | TX | 27.4 | 43.0 | 48.9 | 1,387 -> 1,744 |
| Monroe | LA | 32.5 | 48.0 | 52.7 | 2,431 -> 2,811 |
| CollegeStation | TX | 54.2 | 69.0 | 76.0 | 2,951 -> 3,444 |

## Largest rise in hot nights per year

| City | State | Baseline | Forecast | Observed (check) | cdd baseline -> forecast |
|---|---|---|---|---|---|
| Tampa | FL | 65.2 | 108.7 | 128.0 | 3,493 -> 4,098 |
| WestPalmBeach | FL | 85.6 | 125.5 | 149.4 | 4,014 -> 4,546 |
| Houston | TX | 39.4 | 76.1 | 87.9 | 2,974 -> 3,494 |
| CollegeStation | TX | 35.8 | 71.2 | 86.0 | 2,951 -> 3,444 |
| CorpusChristi | TX | 68.1 | 103.5 | 104.4 | 3,495 -> 4,037 |
| Gulfport | MS | 38.9 | 72.7 | 72.2 | 2,626 -> 3,052 |
| LakeCharles | LA | 42.4 | 70.8 | 70.3 | 2,747 -> 3,192 |
| Miami | FL | 123.7 | 151.8 | 168.3 | 4,417 -> 4,971 |
| Pensacola | FL | 42.0 | 68.9 | 81.0 | 2,632 -> 3,034 |
| DallasFortWorth | TX | 46.8 | 71.8 | 69.7 | 2,706 -> 3,192 |
| Austin | TX | 49.3 | 74.1 | 82.9 | 3,045 -> 3,593 |
| SanAntonio | TX | 59.7 | 83.4 | 85.9 | 3,085 -> 3,565 |
| Tucson | AZ | 32.2 | 55.6 | 66.2 | 3,150 -> 3,643 |
| ElPaso | TX | 8.5 | 31.4 | 43.7 | 2,280 -> 2,904 |
| Shreveport | LA | 21.8 | 44.0 | 56.0 | 2,459 -> 2,945 |

## Limits

- Stations are mostly at airports, outside dense city centres, so heat where people live is probably understated (urban heat island).
- Dry-bulb lines only: the data has no humidity, so humid cities' risk is understated (essay section 1b).
- The delta method shifts the whole distribution by the shared slope; it does not change the shape of heat waves.
