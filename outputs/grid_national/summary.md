# Section 3 (national): how heat moves electricity demand, by U.S. region

Hourly demand: EIA-930, July 2015 - December 2018 (13 EIA regions). Temperatures: challenge daily data, challenge cities in each region weighted by county households. Summer = June-September. All data up to 2018.

**Contiguous U.S. (all 13 regions, 412 summer days): +13,663 MW of daily peak per 1 F of the household-weighted daily high (se 293), 2.2% per F; R squared 0.88.**

| Region | Cities | Summer days | Peak: MW per F | Peak: % per F | Night floor: MW per F | Night: % per F | Fit (day / night) | 2018 summer mean peak (MW) | Winter-peaking years 2016-18 |
|---|---|---|---|---|---|---|---|---|---|
| FLA | 10 | 439 | 1,438 | 3.4% | 665 | 3.0% | 0.84 / 0.64 | 41,894 | 0 of 3 |
| CAL | 11 | 456 | 898 | 2.1% | 417 | 1.5% | 0.76 / 0.66 | 43,725 | 0 of 3 |
| MIDA | 28 | 456 | 2,428 | 2.0% | 1,134 | 1.4% | 0.83 / 0.76 | 119,280 | 0 of 3 |
| TEX | 8 | 457 | 1,266 | 2.0% | 833 | 2.1% | 0.95 / 0.84 | 62,718 | 0 of 3 |
| TEN | 3 | 443 | 502 | 2.0% | 221 | 1.5% | 0.89 / 0.82 | 25,124 | 2 of 3 |
| CAR | 6 | 458 | 716 | 2.0% | 325 | 1.6% | 0.93 / 0.77 | 36,105 | 1 of 3 |
| NY | 5 | 458 | 461 | 1.9% | 263 | 1.7% | 0.83 / 0.78 | 24,108 | 0 of 3 |
| MIDW | 47 | 458 | 1,935 | 1.8% | 842 | 1.2% | 0.91 / 0.84 | 106,488 | 0 of 3 |
| NE | 6 | 458 | 328 | 1.8% | 220 | 1.8% | 0.83 / 0.82 | 18,138 | 0 of 3 |
| CENT | 24 | 457 | 767 | 1.8% | 360 | 1.3% | 0.86 / 0.75 | 42,662 | 0 of 3 |
| SE | 14 | 457 | 688 | 1.7% | 282 | 1.2% | 0.37 / 0.33 | 39,658 | 1 of 3 |
| SW | 8 | 454 | 247 | 1.4% | 96 | 1.0% | 0.44 / 0.37 | 17,463 | 0 of 3 |
| NW | 29 | 454 | 534 | 1.2% | 247 | 0.8% | 0.61 / 0.49 | 46,300 | 1 of 3 |

- Median region: 1.9% more peak demand per F of daily high; 1.5% higher overnight floor per F of daily low.
- Regions whose yearly peak came in winter at least once in 2016-2018: TEN, CAR, SE, NW.

## Limits

- Only 3.5 summers (EIA-930 starts July 2015); ERCOT's own 2002-2018 record (code/policy_grid_ercot.py) is the long-run check.
- Regions are EIA's groupings of balancing authorities; cities are assigned by state, which is approximate at borders.
- Load is what customers drew; on emergency days demand was cut, so heat's effect is understated.
- Airport temperatures; regions with few challenge cities have noisier temperatures.
