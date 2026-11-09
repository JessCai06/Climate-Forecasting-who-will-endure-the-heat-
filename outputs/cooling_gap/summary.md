# The cooling gap: homes without AC meeting heat they were not built for

Cities: 199. Heat threshold = each city's 1976-2005 99th percentile of daily highs. Forecast heat days use data up to 2018 only (delta method, shared Tmax slope 0.0484 F/yr). Homes without AC: Census LACE 2023 (experimental). Built environment and people: CDC/ATSDR Heat & Health Index 2024.

Check of the forecast against what happened (analysis only): median heat days/yr 1976-2005 4.4, forecast 2019-2025 5.1, observed 5.1; rank correlation forecast vs observed across cities 0.51.

## A. Largest cooling gaps per household (share without AC x forecast heat days/yr)

| City | County | No AC % | Heat days/yr 1976-2005 | Forecast 2019-25 | Observed 2019-25 | Uncooled heat-days per household | Households without AC |
|---|---|---|---|---|---|---|---|
| Seattle | King County, WA | 46.9 | 3.8 | 7.9 | 7.7 | 3.71 | 435,146 |
| Astoria | Clatsop County, OR | 63.8 | 4.0 | 5.7 | 6.9 | 3.65 | 11,546 |
| Ukiah | Mendocino County, CA | 43.5 | 4.7 | 7.7 | 12.9 | 3.36 | 15,038 |
| Clayton | Union County, NM | 19.9 | 4.2 | 14.8 | 8.3 | 2.95 | 299 |
| Eureka | Humboldt County, CA | 63.4 | 4.5 | 4.3 | 5.0 | 2.73 | 34,795 |
| Helena | Lewis and Clark County, MT | 31.4 | 4.3 | 6.5 | 11.0 | 2.04 | 9,625 |
| Lander | Fremont County, WY | 24.6 | 4.8 | 7.5 | 9.1 | 1.85 | 3,642 |
| ColoradoSprings | El Paso County, CO | 24.5 | 4.4 | 7.5 | 8.7 | 1.84 | 69,380 |
| Missoula | Missoula County, MT | 28.4 | 4.8 | 6.2 | 13.0 | 1.76 | 14,668 |
| SanDiego | San Diego County, CA | 25.8 | 3.8 | 6.8 | 4.9 | 1.75 | 299,246 |
| Ely | White Pine County, NV | 31.9 | 3.7 | 5.3 | 8.0 | 1.69 | 1,087 |
| EUGENE | Lane County, OR | 28.9 | 3.9 | 5.7 | 8.4 | 1.65 | 46,099 |
| Bluefield | Mercer County, WV | 13.3 | 5.5 | 11.0 | 3.3 | 1.47 | 3,245 |
| Elko | Elko County, NV | 18.8 | 3.7 | 6.9 | 6.6 | 1.30 | 3,674 |
| SaultSteMarie | Chippewa County, MI | 27.6 | 4.6 | 4.6 | 5.1 | 1.27 | 3,828 |

## A. Largest totals (households without AC x forecast heat days/yr)

| City | County | Households without AC | Forecast heat days/yr | Uncooled household heat-days/yr |
|---|---|---|---|---|
| Seattle | King County, WA | 435,146 | 7.9 | 3,438,342 |
| LosAngeles | Los Angeles County, CA | 701,788 | 4.2 | 2,948,761 |
| SanDiego | San Diego County, CA | 299,246 | 6.8 | 2,035,285 |
| ColoradoSprings | El Paso County, CO | 69,380 | 7.5 | 520,118 |
| Detroit | Wayne County, MI | 63,115 | 6.2 | 391,046 |
| Cleveland | Cuyahoga County, OH | 41,555 | 7.7 | 319,818 |
| Buffalo | Erie County, NY | 51,496 | 5.7 | 293,404 |
| EUGENE | Lane County, OR | 46,099 | 5.7 | 262,831 |
| RochesterNY | Monroe County, NY | 38,923 | 5.8 | 225,642 |
| Houston | Harris County, TX | 22,485 | 9.8 | 220,442 |

## B. Archetypes (k-means, k = 4; agreement across 50 starts: 76%)

| Archetype | Cities | Median lat | No AC % | Heat-day rise (fc) | Impervious % | Canopy % | Poverty % | Living alone % | Households without AC (sum) | Example cities |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 15.0 | 44.1 | 28.9 | +1.4 | 3 | 35 | 25 | 16 | 627,498 | Seattle, Astoria, Ukiah, Eureka, Helena, Lander |
| 1 | 86.0 | 41.0 | 1.4 | +0.5 | 24 | 14 | 22 | 17 | 634,784 | Clayton, Buffalo, RochesterNY, Cheyenne, Havre, GreatFalls |
| 2 | 60.0 | 35.4 | 1.8 | +0.8 | 11 | 42 | 27 | 16 | 162,683 | Bluefield, Erie, Beckley, Concord, Duluth, KlamathFalls |
| 3 | 38.0 | 34.4 | 1.4 | +2.8 | 30 | 6 | 25 | 12 | 1,286,285 | ColoradoSprings, SanDiego, Elko, Reno, Winnemucca, LosAngeles |
