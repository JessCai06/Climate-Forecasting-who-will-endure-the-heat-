# Policy heuristic check: candidate data sources

Status: step 1 of the policy check plan (source discovery), 2026-11-08. Nothing below is used in any forecast.
"Tested" means we queried the source from this machine on 2026-11-08 and got the numbers shown.

## Weather (stand-in for the forecast)

| Source | Coverage | Status |
|---|---|---|
| NOAA GHCN-Daily, per-station CSV (`code/fetch_truth.py`) | 2021-01-01 to 2025-12-31, written to `obs_2021_2025.csv` | **Tested.** 209 of 210 stations. `USW00094014` has no data after 2020-01-06 (station closed). Stations with ≤10 missing TMAX days: 205 (2021), 206 (2022), 207 (2023), 203 (2024), 198 (2025). The 2021 rows match `obs_2018_2021.csv` exactly. |
| Challenge `annual_indices` | Baselines 1976-2005 and 1989-2018 | Already in use. |

Post-2018 observations: analysis only, user-approved 2026-11-08. Never a forecast input; to be replaced by the forecast or labelled "observed".

## Buildings: all 210 cities (proxy for mixed-use stock)

| Source | Gives | Status |
|---|---|---|
| Census ACS 5-year, B25024 (units in structure), B25034 (year built), B25003 (tenure), by county | Small multifamily (2-19 units) and pre-1980 share | **The API now requires a key** ("Missing Key" page, HTTP 302). A free key needs a sign-up a team member must do. **Keyless alternative tested:** the ACS table-based summary file downloads without a key (`www2.census.gov/.../acsdt5y2023-b25024.dat`, 47.8 MB). |
| FCC Area API (lat/lon to county FIPS) | Link each station to its county | **Tested.** Pittsburgh's station `USW00094823` is in Allegheny County, FIPS 42003. No key needed. |
| ORNL USA Structures, USACE National Structure Inventory | Building footprints and occupancy | Not verified. We found no documentation of a mixed-use occupancy class. |

## Buildings: case-study cities (actual mixed-use counts)

| City | Source | Mixed-use code | Status |
|---|---|---|---|
| Pittsburgh (Allegheny County) | WPRDC Property Assessments (CKAN datastore, resource `65855e14-...`) | `USEDESC` = `RETL/APT'S OVER` (3,272 parcels), `OFFICE/APARTMENTS OVER` (828) | **Tested.** 4,100 parcels. **Finding:** both are classed COMMERCIAL, and year built is recorded for only 99 of the 4,100 (2.4%). The county records building details only for residential parcels, so apartments over shops are missing them. |
| New York City | DCP PLUTO (Socrata `64uk-42ks`) | `landuse = 04` (mixed residential and commercial) | **Tested.** 56,272 lots, mean year built 1928. Check the code wording in the PLUTO data dictionary. |
| Chicago (Cook County) | Assessor Parcel Universe (Socrata `pabr-t5kh`) | `class = 212` (mixed-use, 6 units or fewer); `318` (mixed-use, 7+ units, under-size limits) | **Tested.** 212: 13,853 parcels; 318: 3,179. Class definitions to confirm in the Assessor's class code PDF (sources disagree on the 318 rule). |

## Air conditioning

| Source | Gives | Status |
|---|---|---|
| American Housing Survey | Central / room / no AC | Metro-level only for selected metros and years; no single current metro table found. |
| EIA RECS 2020 | AC by region (state estimates to confirm) | Not tested. |

## Policy

| Source | Gives | Status |
|---|---|---|
| PNNL, *Guide to Determining Climate Zone by County*, 2021 IECC (PNNL-33270, data files on basc.pnnl.gov) | Energy-code climate zone per county | Found, not downloaded. Lets us compare each zone's assumed cdd with the observed cdd. |
| Building performance standards (IMT policy map; city ordinances) | Size thresholds | No machine-readable list found. Reported: NYC LL97 25,000 sq ft; Boston BERDO 20,000 sq ft; DC phase-dependent. Compile by hand from ordinances. |
| Rental cooling requirements (news reports; municipal codes) | Indoor maximum temperature | No authoritative list found. Reported: LA County 82 °F (from 2027), Palm Springs 80 °F, Phoenix, Tempe, Montgomery County MD 80 °F, Dallas, El Paso, Houston, Austin, NYC 78 °F by 2030. Each to confirm in the code text. |
| ASHRAE design conditions | Design temperatures | Copyrighted; not usable openly. Use 1976-2005 values from the challenge data as the design baseline instead. |

## Feedback items found so far (for the README)

1. Census ACS API now requires a key; the keyless summary file works but is a 48 MB download per table.
2. Allegheny County records year built for only 2.4% of apartments-over-shops parcels, because they are classed commercial.
3. Every city codes mixed use differently (`USEDESC` text, PLUTO `landuse 04`, Cook class `212`/`318`); there is no shared standard.
4. No national dataset counts mixed-use buildings; no machine-readable list of BPS thresholds or rental cooling rules.
5. ASHRAE design conditions are copyrighted, so design-weather drift cannot be checked against them openly.

## Sources

- PLUTO data dictionary: https://s-media.nyc.gov/agencies/dcp/assets/files/pdf/data-tools/bytes/PLUTODD.pdf
- Cook County class codes: https://prodassets.cookcountyassessor.com/s3fs-public/form_documents/Class_codes_definitions_12.16.24.pdf
- Cook County classifications: https://www.cookcountyassessoril.gov/classifications-real-property
- WPRDC property assessments: https://catalog.data.gov/dataset/allegheny-county-property-assessments/resource/78f76bd9-b58f-4a87-9009-2e8598552f0a
- PNNL climate zone files: https://basc.pnnl.gov/guide-determining-climate-zone-county-data-files
- Rental cooling laws (reporting): https://www.multifamilydive.com/news/tenant-right-cooling-laws-cities-extreme-heat-indoor-maximum-temperature/725113/
- LA County 82 °F: https://laist.com/news/housing-homelessness/los-angeles-county-cooling-air-conditioning-temperature-82-degrees-requirement-landlord-rental-housing
- BPS overview (DOE): https://www.energycodes.gov/sites/default/files/2023-05/2023_NECC_BPS_Panel.pdf
- AHS AC by metro (study): https://www.nature.com/articles/s41370-020-0220-8
