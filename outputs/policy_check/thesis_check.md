# Policy heuristic check

Weather input: **OBSERVED NOAA GHCN-Daily 2019-2025 (stand-in, analysis only)**. Thresholds were fixed in `config.json` before the results were computed.

## Verdict

- Cities with all three flags (heat past design, older small multifamily stock, no cooling rule): **18 of 210 (9%)**. Threshold for 'supported': 20%. **Thesis NOT supported** at an indoor limit of 80 F.
- Indoor limit sensitivity: 78 F: 17 cities (not supported); 80 F: 18 cities (not supported); 82 F: 21 cities (not supported).

## The three claims

| Claim | Cities flagged | Evaluable |
|---|---|---|
| H1 heat past design (1976-2005 baseline) | 56 | 196 |
| H2 above-median older small multifamily share (by construction about half) | 105 | 210 |
| H3 no in-force rental cooling rule covering small buildings | 206 | 210 (checked by hand for 9 cities) |

Across the 196 cities with enough data: median cdd change +22%, median hottest-day change +1.0 F; cdd rose in 97% of them and the hottest day rose in 78%.

## Post-hoc breakdown (looked at after the verdict; does not change it)

- Cooling **energy** claim alone (cdd at least 10% above baseline, baseline cdd at least 100): 173 cities; with H2 and H3 as well: 84.
- **Peak** heat claim alone: hottest day at least 2 F above baseline in 44 cities; capacity shortfall at least 10% in 50.
- H1 rate among cities with above-median older small multifamily stock: 19%; among the rest: 38%.

## Cities with all three flags (largest cooling-load increase first)

| City | County | cdd 1976-2005 | cdd 2019-2025 | Cooling load change | Hottest day change F | Capacity shortfall | Small MF share | Pre-1980 share |
|---|---|---|---|---|---|---|---|---|
| Astoria | Clatsop County, OR | 14 | 43 | +200% | +6.6 | 119% | 18% | 58% |
| Salem | Marion County, OR | 268 | 573 | +114% | +4.2 | 21% | 20% | 52% |
| EUGENE | Lane County, OR | 237 | 474 | +100% | +4.5 | 23% | 16% | 56% |
| Missoula | Missoula County, MT | 266 | 451 | +69% | +2.4 | 13% | 19% | 46% |
| Pullman | Whitman County, WA | 233 | 374 | +61% | +3.4 | 19% | 37% | 54% |
| Burlington | Chittenden County, VT | 493 | 754 | +53% | +1.9 | 14% | 25% | 49% |
| Glasgow | Valley County, MT | 504 | 744 | +48% | +5.0 | 24% | 23% | 79% |
| Portland | Multnomah County, OR | 386 | 562 | +45% | +2.6 | 13% | 19% | 61% |
| Worcester | Worcester County, MA | 454 | 644 | +42% | +1.4 | 12% | 28% | 65% |
| Buffalo | Erie County, NY | 554 | 750 | +35% | +1.6 | 15% | 30% | 77% |
| GrandForks | Grand Forks County, ND | 415 | 543 | +31% | +1.9 | 12% | 19% | 49% |
| Amarillo | Potter County, TX | 1387 | 1789 | +29% | +4.1 | 19% | 14% | 71% |
| Williamsport | Lycoming County, PA | 729 | 931 | +28% | +1.9 | 12% | 15% | 71% |
| Fresno | Fresno County, CA | 2061 | 2618 | +27% | +2.5 | 9% | 18% | 49% |
| Shreveport | Caddo Parish, LA | 2459 | 3096 | +26% | +2.5 | 12% | 16% | 59% |
| Abilene | Taylor County, TX | 2431 | 3020 | +24% | +4.3 | 18% | 17% | 54% |
| Nashville | Davidson County, TN | 1674 | 2066 | +23% | +1.8 | 10% | 21% | 42% |
| BatonRouge | East Baton Rouge Parish, LA | 2652 | 3238 | +22% | +2.0 | 11% | 20% | 44% |

## Evidence against the thesis

- Heat past design but **little** older small multifamily stock (38): Natchitoches, Flagstaff, Beckley, KeyWest, Miami, Tampa, SanAntonio, Galveston, Houston, Raleigh, Lynchburg, Mobile, Austin, Muskegon, Duluth, Roswell, ElPaso, Clayton, Goodland, GrandJunction ...
- Lots of older small multifamily stock but heat **not** past design (79): NewBrunswick, Denver, Macon, Augusta, Savannah, DallasFortWorth, Cleveland, Gainesville, CorpusChristi, Morgantown, NorfolkVA, Philadelphia, WashingtonDC, Wilmington, Hattiesburg, Meridian, Charleston, Athens, Atlanta, Birmingham ...
- Cities with a cooling rule in force: DallasFortWorth, Austin, ElPaso, Phoenix

## Case studies (actual mixed-use buildings)

| City | Mixed-use buildings | Year built recorded | Built before 1980 | Below size limit of building rules | Central AC |
|---|---|---|---|---|---|
| Pittsburgh | 4,100 | 2% | 98% | n/a (limit 50,000 sq ft) | n/a |
| NewYork | 56,272 | 100% | 88% | 88% (limit 25,000 sq ft) | n/a |
| Chicago | 14,114 | 100% | 95% | 100% (limit 50,000 sq ft) | 44% |

- **Pittsburgh**: cdd 735 -> 941 (+28%), hottest day 92.8 -> 92.7 F; H1 False, H2 True, H3 gap (checked).
- **NewYork**: cdd 1159 -> 1280 (+10%), hottest day 97.4 -> 96.1 F; H1 False, H2 True, H3 gap (checked).
- **Chicago**: cdd 844 -> 1157 (+37%), hottest day 97.3 -> 97.1 F; H1 False, H2 True, H3 gap (checked).

## Method limits (state these with any result)

- H1 compares 2019-2025 with 1976-2005 at the station. Most stations are at airports, outside the dense centres where mixed-use buildings are, so heat there is probably understated (urban heat island).
- Capacity shortfall uses (T_hot_new - T_in) / (T_hot_design - T_in) - 1; steady-state, ignores sun, people, equipment and humidity. The design temperature is approximated by the mean annual hottest day, not the ASHRAE 0.4%/1% design values (copyrighted).
- Cooling load change uses the degree-day method: cooling energy taken as proportional to cdd.
- H2 is a county proxy: ACS counts building size and age, not mixed use, and cannot cross them (exposure = product of the two shares). The station's county may differ from the city's.
- H3 relies on reported rules (data/policy_rules.csv); most cities were not checked in their municipal code, so 'gap (not checked)' means no rule was found in national reporting, not that none exists.
- The weather input is observed data used as a stand-in for the forecast; rerun with `--weather submission.csv`.