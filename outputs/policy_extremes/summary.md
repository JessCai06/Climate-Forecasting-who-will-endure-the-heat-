# Are cities seeing heat and cold they were not built for?

Design range = each city's own 1976-2005 record. Recent = observed NOAA 2019-2025 (analysis only). Definitions fixed in `config.json` before the results.

Cities with enough data: 199 (91 north of 40 N, 108 south).

| | Group | Days/yr past the 1% level: 1976-2005 -> 2019-2025 (median city) | Days/yr in runs of 3+ (median) | Cities where runs of 3+ rose | Cities beyond their 1976-2005 record (no-change: 19%) |
|---|---|---|---|---|---|
| heat | all | 4.4 -> 5.1 | 1.8 -> 1.9 | 49% | 24% (48) |
| heat | north | 4.2 -> 4.7 | 1.5 -> 1.3 | 47% | 24% (22) |
| heat | south | 4.4 -> 5.6 | 2.3 -> 2.4 | 51% | 24% (26) |
| cold | all | 4.0 -> 1.4 | 1.6 -> 0.4 | 12% | 12% (24) |
| cold | north | 3.9 -> 1.6 | 1.6 -> 0.5 | 9% | 14% (13) |
| cold | south | 4.1 -> 1.4 | 1.6 -> 0.4 | 14% | 10% (11) |

## Largest rise in heat-run days per year

| City | Lat | Threshold F | Run days/yr 1976-2005 | 2019-2025 | Longest run 1976-2005 | 2019-2025 | Record then | 2019-2025 extreme |
|---|---|---|---|---|---|---|---|---|
| Austin | 30.3 | 102 | 2.4 | 23.3 | 7 | 45 | 112 | 110 |
| CorpusChristi | 27.8 | 98 | 3.3 | 18.6 | 10 | 44 | 109 | 105 |
| CollegeStation | 30.6 | 102 | 2.2 | 13.9 | 7 | 29 | 112 | 112 |
| Needles | 34.8 | 116 | 2.3 | 13.2 | 8 | 9 | 125 | 123 |
| Abilene | 32.4 | 103 | 1.9 | 12.0 | 6 | 14 | 110 | 113 |
| SanAntonio | 29.5 | 101 | 2.4 | 12.3 | 9 | 18 | 111 | 108 |
| BatonRouge | 30.5 | 97 | 1.5 | 11.0 | 8 | 23 | 105 | 106 |
| Roswell | 33.3 | 104 | 1.7 | 11.0 | 11 | 12 | 114 | 112 |
| Phoenix | 33.4 | 113 | 1.8 | 10.7 | 9 | 17 | 122 | 119 |
| ElPaso | 31.8 | 105 | 2.8 | 10.4 | 10 | 8 | 114 | 112 |
| Houston | 30.0 | 100 | 3.3 | 10.3 | 14 | 23 | 109 | 109 |
| SaltLakeCity | 40.8 | 100 | 2.6 | 9.4 | 10 | 9 | 107 | 107 |
| Missoula | 46.9 | 96 | 2.0 | 8.7 | 9 | 8 | 104 | 104 |
| Reno | 39.5 | 100 | 1.9 | 8.4 | 10 | 10 | 108 | 108 |
| Tampa | 28.0 | 95 | 1.7 | 7.0 | 6 | 9 | 99 | 100 |

## Largest rise in cold-run days per year

| City | Lat | Threshold F | Run days/yr 1976-2005 | 2019-2025 | Longest run 1976-2005 | 2019-2025 | Record then | 2019-2025 extreme |
|---|---|---|---|---|---|---|---|---|
| Eureka | 40.8 | 32 | 1.7 | 5.3 | 7 | 8 | 22 | 27 |
| Portland | 45.5 | 27 | 3.0 | 4.0 | 8 | 6 | 8 | 12 |
| TriCities | 46.3 | 12 | 2.5 | 3.3 | 9 | 7 | -19 | -7 |
| Denver | 39.8 | -4 | 1.7 | 2.3 | 9 | 4 | -25 | -24 |
| LakeCharles | 30.1 | 27 | 1.2 | 1.7 | 4 | 5 | 11 | 6 |
| GreatFalls | 47.5 | -19 | 2.0 | 2.4 | 6 | 6 | -42 | -37 |
| SanAntonio | 29.5 | 25 | 1.7 | 2.1 | 8 | 4 | 6 | 9 |
| Oklahoma | 35.4 | 10 | 1.8 | 2.1 | 8 | 4 | -8 | -14 |
| Clayton | 36.4 | 4 | 2.2 | 2.4 | 6 | 4 | -14 | -15 |
| Austin | 30.3 | 25 | 2.2 | 2.4 | 9 | 6 | 4 | 7 |
| Harrison | 36.3 | 6 | 1.6 | 1.9 | 5 | 4 | -13 | -9 |
| McCook | 40.2 | -6 | 1.6 | 1.8 | 9 | 4 | -23 | -24 |
| Hastings | 40.6 | -8 | 1.4 | 1.6 | 8 | 4 | -23 | -30 |
| CorpusChristi | 27.8 | 31 | 1.5 | 1.7 | 5 | 5 | 13 | 17 |
| PineBluff | 34.2 | 17 | 1.8 | 2.0 | 5 | 7 | 2 | 0 |
