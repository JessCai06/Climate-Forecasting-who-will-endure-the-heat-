# Section 3: ERCOT, the grid as it has been (2002-2018)

Hourly load: ERCOT native load archives. Temperature: challenge daily data at Houston, Dallas-Fort Worth, Austin, San Antonio, Corpus Christi and Abilene, weighted by zone load (weights cover 5 of 8 zones). All data up to 2018.

## 1. Growth

- Yearly energy: 280 TWh in 2002 -> 376 TWh in 2018 (trend +1.7% a year).
- Yearly peak: 56,068 MW -> 73,308 MW (trend +1.4% a year). The peak fell in summer (June-September) in 17 of 17 years.
- Summer (June-September) share of yearly energy: 40% on average.

| Year | Energy (TWh) | Peak (MW) | Peak date | Hours within 10% of the peak |
|---|---|---|---|---|
| 2002 | 280 | 56,068 | 2002-08-26 | 151 |
| 2003 | 284 | 60,030 | 2003-08-07 | 71 |
| 2004 | 288 | 58,484 | 2004-08-03 | 101 |
| 2005 | 298 | 60,213 | 2005-08-23 | 182 |
| 2006 | 305 | 62,203 | 2006-08-17 | 184 |
| 2007 | 307 | 62,115 | 2007-08-13 | 79 |
| 2008 | 311 | 62,103 | 2008-08-04 | 157 |
| 2009 | 307 | 63,407 | 2009-07-13 | 206 |
| 2010 | 318 | 65,713 | 2010-08-23 | 134 |
| 2011 | 334 | 68,318 | 2011-08-03 | 266 |
| 2012 | 325 | 66,558 | 2012-06-26 | 183 |
| 2013 | 332 | 67,253 | 2013-08-07 | 171 |
| 2014 | 340 | 66,464 | 2014-08-25 | 194 |
| 2015 | 347 | 69,620 | 2015-08-10 | 176 |
| 2016 | 351 | 71,093 | 2016-08-11 | 171 |
| 2017 | 357 | 69,496 | 2017-07-28 | 242 |
| 2018 | 376 | 73,308 | 2018-07-19 | 237 |

## 2. How demand rises with heat (summer days, growth held fixed by year)

| Relationship | Per degree F | As % of the 2018 summer average | Fit (R squared) |
|---|---|---|---|
| Daily peak vs high, below 95 F | 1,202 MW (se 10) | 1.9% | 0.96 |
| Daily peak vs high, 95 F and above | 1,100 MW (extra -101, se 25) | 1.8% | |
| Night low load vs daily low | 663 MW (se 7) | 1.7% | 0.91 |
| Daily energy vs cooling degree days | 23,181 MWh per cdd (se 141) | 1.9% per cdd | 0.96 |

- Summer days analysed: 2,074; days with a weighted Texas high of 95 F or more: 862 (42%).
- 2018 averages: summer daily peak 62,743 MW, overnight low 38,847 MW, daily energy 1,218 GWh.

## Limits

- Load is what customers drew, not what they would have drawn: on emergency days (August 2011) some demand was cut.
- Year effects absorb growth but also any other year-to-year change; the weather slopes assume the same response every year.
- Airport temperatures; three zones (EAST, FWEST, NORTH) have no challenge station.
