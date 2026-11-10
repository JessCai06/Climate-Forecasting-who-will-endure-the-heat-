# Protostar Challenge: Climate Risk Intelligence (full Space export)

Source: https://huggingface.co/spaces/CMU-OSPO/protostar-challenge-climate-risk-intelligence
Captured: 2026-11-07 (page text as of commit d89df2d, "Nov 6 clarifications")
License of the Space: MIT, Copyright (c) 2026 Emma Scharfmann. Content below is copied from the Space's `content/about.md`, `content/data.md`, `config.py` and `tabs/*.py`.

Edits made in this export: the two LaTeX formulas are rewritten in plain text; the rubric table (a placeholder in the original) is filled in from `config.py`; the Registration and Submission tabs are summarized from their code. Nothing else is changed.

## Contents

1. About tab
2. Data & submission tab
3. Registration tab
4. Submission tab
5. Leaderboard and Judging tabs
6. Key config values
7. Repo layout

---

# 1. About tab (`content/about.md`)

## The challenge

**Climate Risk Intelligence: AI systems to analyze extreme weather trends and recommend climate adaptation strategies.**

### The Urban Climate AI Challenge: The 2019–2025 Test

A major Carnegie Mellon climate study (Lai & Dzombak) collected weather records for **210 U.S. cities** from ~1900 up through 2018.

Your job is simple: put yourself at the end of 2018 and **predict the actual yearly weather for each city from 2019 through 2025**, without using any data that reveals how those years turned out. You are welcome to bring in **other data** too (e.g., weather records up to 2018 from other sources, census, land cover, building stock); the data rule below says what can feed your forecasts. We will compare your predictions against the weather actually recorded at airport and city weather stations during those years. Then, use what you learned to propose one **policy idea** that helps a city, or the country, cope with a climate risk.

> **Data rule (honor code):** to forecast **temperature, precipitation, hottest day and CDD**, use only records up to **2018-12-31**: the challenge dataset, or other sources cut at the same date. Do not use **any 2019–2025 data that responds to the weather** as an input to your forecasts: weather observations from any source, and anything driven by them (e.g., streamflow, air quality, energy demand, plant or disease data). This includes numbers produced by AI models that learned from later data (see the FAQ). Other data (e.g., census, land cover, energy, health) is welcome for your analysis and policy idea; list every external source in your README. Examples are in the FAQ (*Data & submission* tab).

**Important dates** (all times ET):

- **Tuesday, November 10, 11:59 PM:** online submission deadline; registration stays open until then.
- **November 11–12:** finalist teams announced.
- **Friday, November 13:** overall winners announced.
- *For CMU teams:*
  - **Tuesday, November 3, 11:59 PM:** registration deadline.
  - **Wednesday, November 4, 11 AM–12 PM:** virtual kickoff on Zoom: challenge overview, resources and Q&A.
  - **Friday, November 13:** in-person presentations of the CMU finalists, where the winning CMU team will be chosen, Hamburg Hall, Room A301, Carnegie Mellon University.

### Important updates

**November 6:** clarifications only; the rules, the scoring, the answer key and the deadline are unchanged.

- Rows not scored: the 10-day rule also applies to the 30 training years of the baselines, and a city–metric needs at least 10 valid years in 1989–2018 to have a baseline (9 city–metrics, 63 rows).
- Practice run: with the official 10-year minimum, the CDD baselines score 212 / 175 °F-days (213 / 177 were computed without it; thanks to Team Zhoey for catching it). The difference is within noise.
- Data rule: choosing or tuning a model by scoring it on 2019–2025 observations counts as using them (FAQ, *Data & submission* tab).

**November 5:** the rules, the scoring and the deadline are unchanged; `daily` and `annual_indices` are unchanged.

- New subset `coverage_and_stations`: for each city and year, the days with both temperatures and the station the record comes from.
- The dataset page now explains which days each value uses, and how missing days and station changes affect the record.
- `city_info`: station start dates are stored as dates (add `.astype(str)` if your code reads them as text); two station-date typos corrected.
- Submission template: `code/requirements.txt` added.

## Teams

Registration is team-based. Each participant can be in one team only. **A maximum of 5 individuals per team.**

**CMU team:** a team counts as a CMU team, and can win the CMU prize, when **more than half of its members are current Carnegie Mellon University students** (e.g., 2 of 3, 3 of 4, or 3 of 5). CMU students must register with their CMU email (`@andrew.cmu.edu`). Team membership at the deadline counts.

## What your model predicts

For each of the 210 cities, predict a single number for each year from 2019 through 2025 for four metrics:

| Metric | `metric` code | Unit | Description |
|---|---|---|---|
| **Average Annual Temperature** | `annual_avg_temp` | °F | The overall yearly average temperature. |
| **Total Annual Precipitation** | `total_precip_in` | inches | Total liquid moisture (rain plus melted snow) recorded for the year. |
| **Hottest Day of the Year** | `hottest_day_temp` | °F | The single highest daily peak temperature recorded that year. |
| **Cooling Degree Days (CDD)** | `cdd` | °F-days | A single yearly number that adds up how many degrees each day's average temperature rose above 65 °F; used to estimate how much air conditioning a city needs. |

### How CDD is computed

```
CDD = sum over d = 1..D of  max(0, (Tmax_d + Tmin_d) / 2 - 65)
```

- **D:** the number of days in the year (365 or 366).
- **Tmax_d and Tmin_d:** that day's highest and lowest temperatures, in °F.
- **max(0, ...):** a day at or below 65 °F adds nothing.

**Example:** a day with a high of 90 °F and a low of 70 °F averages 80 °F, so it adds 80 − 65 = 15 to the year's CDD.

No probabilities or intervals required: just your model's best guess for each value.

## How the forecasts are scored

Each metric is scored with **Mean Absolute Error (MAE)**, the average gap between your prediction and what actually happened (lower is better):

```
MAE = (1/N) * sum over i of |Predicted_i - Actual_i|
```

The four metrics use different units, so each one is compared against the 30-year-average baseline. The **Score** says how much better than that baseline your model was:

```
S_m   = 1 - MAE_m(your model) / MAE_m(30-year average)
Score = 100 * max(0, (S_temp + S_precip + S_hot + S_cdd) / 4)
```

**Score = 0:** no better than the 30-year average. **Score = 100:** a perfect forecast. Higher is better.

| Score | Years scored |
|---|---|
| **Live Score** | 2019–2021 |
| **Final Score** | 2022–2025 |

The two are kept separate on purpose: a model tuned to 2019–2021 does not necessarily predict later years well.

> **Note:** a few rows are not scored: years where the station missed more than 10 days of the values a metric uses (daily maximum and minimum temperature for average temperature, hottest day and CDD; daily precipitation for total precipitation), and city–metrics with fewer than 10 valid years in 1989–2018 (the same 10-day rule), which have no baseline: 9 city–metrics, 63 rows. Predict every row anyway.

## Live leaderboard

Your **Live Score** (2019–2021) appears on the leaderboard **a few hours** after you submit. Use it to **check how your model is doing** as you improve it; the final ranking and the winners are decided after the deadline (see *Judging*). If you have questions, post in the Space's [Community tab](https://huggingface.co/spaces/CMU-OSPO/protostar-challenge-climate-risk-intelligence/discussions).

## What to beat

The leaderboard includes three simple reference baselines:

1. **Last Year Repeated:** every year from 2019 to 2025 repeats the city's last valid value (2018 for most cities).
2. **30-Year Average:** every year equals the city's average from 1989 to 2018.
3. **Linear Trend:** a straight line through the last 30 years, extended out to 2025.

> **Target:** if your model cannot beat the 30-year average, it is probably overfitting to historical noise. Hottest day and precipitation are noisy: matching the 30-year average on them is already reasonable; most of the gain is in temperature and CDD.

> **CDD target:** beat the 30-year average (level 1), then the linear trend (level 2). In a practice run (train up to 2010, predict 2011–2018), the 30-year average scores an MAE of **212 °F-days** and the trend line **175 °F-days**, using the official rule of at least 10 valid years in the 30-year window. Thanks to **Team Zhoey** for spotting that the earlier figures (213 / 177) were computed without that rule. CDD differences under **10 °F-days** are within year-to-year noise.

## Policy idea

Write a short *Policy Idea* section (half a page at most) in your submission's README.

**The task, in one sentence:** using what you learned from the data, suggest one idea that could help a city, or the country, cope with a climate risk sustainably. Answer these three questions however you like:

1. **What risk did you notice?** E.g., more cooling days, hotter peak days, wetter or drier years.
2. **What would you do about it, and who would do it?** A city, a state, the federal government, a utility, a school, a business: your choice.
3. **Why is it sustainable?** It helps without making emissions or costs worse in the long run.

Any city, group of cities or the whole U.S.; any risk in the data; bold ideas welcome. Inspiration: [EPA Heat Island Reduction](https://www.epa.gov/heatislands), [heat.gov](https://www.heat.gov).

## What you submit

**A link to your Hugging Face dataset**, containing your forecasts (`submission.csv`), a README with your method, the AI tools you used, policy idea and feedback to the ecosystem, your code (`code/`), and the curated data it uses (`data/`), so anyone can reproduce your forecasts. **Which data you can curate, and how to use AI agents, is covered in the FAQ (*Data & submission* tab).**

You can revise and submit **up to 10 times a day** until the deadline. **Your latest valid submission counts.** Details are in the *Data & submission* tab.

## Judging

After the submission deadline, a panel of 3–4 judges selects the **finalist teams** (announced November 11–12). The **overall winners** are announced on **Friday, November 13**.

> **For CMU teams:** CMU finalists present their work in person on Friday, November 13 (Hamburg Hall, Room A301, Carnegie Mellon University), where the winning CMU team will be chosen.

Judges use six criteria (the original page renders this table from `config.py`; weights and descriptions below are from there):

| Criterion | Weight | What judges consider |
|---|---:|---|
| Demonstrated Reuse & Extensibility | 25% | Meaningful use or rigorous attempted reuse of ProtoStar artifacts; useful extension, diagnosis, or recommendation for future researchers. Evidence about discovery and reuse friction is scored under Feedback to the Ecosystem, not here. |
| Interoperability & Integration | 20% | Successful combination or portability across repositories, institutions, agencies, environments, or domains, or rigorous evidence showing why integration fails; value and limits of common standards and machine-actionable formats. |
| Reproducibility & Openness | 20% | Ability for others to reproduce the work using provided materials; for submissions declared in advance as negative results, a well-documented attempt that isolates why reproduction is not possible with the available artifact, its metadata, or its documented environment. Recommendations arising from that finding are scored under Feedback to the Ecosystem, not here. |
| Scientific, Research, or Societal Value | 15% | Useful knowledge, new research capability, improved decision-making, or meaningful public benefit. |
| Feedback to the Ecosystem | 15% | Specific, actionable evidence about barriers, failed reuse or reproduction, metadata issues, licensing, documentation, infrastructure, policy, or other opportunities for improvement. |
| Technical Creativity | 5% | Novel methods, AI approaches, technical solutions, or combinations of resources that advance the goals of the challenge. |

Judges consider your **Score** and method under *Scientific, Research, or Societal Value* and *Technical Creativity*, and your **policy idea** under *Scientific, Research, or Societal Value*. **Together these two criteria carry 20% of the rubric's weight: the Score is evidence the judges read, not points added to their evaluation.**

Write your **Feedback to the Ecosystem** in its own section of your README: what got in the way (data, metadata, documentation, licensing, tools) and what would fix it.

If your main finding is that reuse or reproduction did not work, set **Negative result: yes** at the top of your README; the version recorded at your latest submission counts.

Explain not just what you built, but **why it is innovative, who would use it, and whether it could actually work in the real world.**

## Prizes

| Place | Prize |
|---|---|
| **First place team** | $1,000 in Hugging Face credits |
| **Second place team** | $500 in Hugging Face credits |
| **Third place team** | $250 in Hugging Face credits |
| **Top-placing CMU team** | $2,500, shared among the team members. A CMU team is one where more than half of the members are current CMU students (see *Teams*). |

If the top-placing CMU team also places in the top three, it receives that place's Hugging Face credits as well.

---

# 2. Data & submission tab (`content/data.md`)

## Data

One dataset, with daily and yearly weather for 210 U.S. cities up to **2018-12-31**:

**[CMU-OSPO/protostar-climate-train-to-2018](https://huggingface.co/datasets/CMU-OSPO/protostar-climate-train-to-2018)**

| Subset | Rows | Content |
|---|---:|---|
| `daily` | 10,245,754 | Daily `tmax`, `tmin` (°F) and `prcp` (inches) per city, 1851–2018 |
| `annual_indices` | 28,052 | One row per city and year: averages, totals, extremes, `cdd`, and `Miss *` counts of missing days |
| `city_info` | 461 | Station `ID`, city `Name`, latitude, longitude, and the stations joined for each city |
| `coverage_and_stations` | 28,052 | One row per city and year: how many days have both temperatures (the days `cdd` uses), and which station the record comes from |

```python
from datasets import load_dataset

REPO = "CMU-OSPO/protostar-climate-train-to-2018"
daily = load_dataset(REPO, "daily", split="train").to_pandas()
annual = load_dataset(REPO, "annual_indices", split="train").to_pandas()
cities = load_dataset(REPO, "city_info", split="train").to_pandas()
coverage = load_dataset(REPO, "coverage_and_stations", split="train").to_pandas()
```

**Metric codes and their columns in `annual_indices`:** `annual_avg_temp` = `Avg Temp`, `total_precip_in` = `ToT Prcp`, `hottest_day_temp` = `Max Tmax`, `cdd` = `cdd`.

The dataset page describes each subset and its columns. Its *Limitations* section explains missing days and station changes, which can shift a city's record; `coverage_and_stations` marks both.

### Other data is welcome

The challenge dataset is a starting point, not a limit. You can combine it with data from other sources:

- ✅ **As forecast inputs:** weather records **up to 2018-12-31** from any source (e.g., NOAA, ERA5), and data from **any year** that does not respond to the year's weather (e.g., census, land cover, tree canopy, elevation, building stock).
- ❌ **Not as forecast inputs:** any **2019–2025** data that responds to the weather: weather observations from any source, and anything driven by them (e.g., streamflow, air quality, energy demand). It is still welcome in your analysis and policy idea.

The test is not whether the data is *correlated* with the weather (latitude and land cover are, and they are fine), but whether a 2019–2025 value would have been different in a hotter or wetter year. Examples are in the FAQ below. List every external source in your README.

## How to submit

**Your submission is a Hugging Face dataset.** Build it like any dataset on the Hub, then submit its link.

1. **Create your dataset** by copying the template [CMU-OSPO/protostar-climate-submission-template](https://huggingface.co/datasets/CMU-OSPO/protostar-climate-submission-template) into your Hugging Face account.
2. **Add your forecasts** in the template's `submission.csv`: the city, year and metric of all 5,880 rows are already filled in; fill in `predicted_value` (format below). `code/check_submission.py` in the template runs the same checks as the Space (install its packages with `pip install -r code/requirements.txt`).
3. **Write your `README.md`:** your method in a few lines, your **Policy Idea** and your **Feedback to the Ecosystem** (see the *About* tab). It is your write-up.
4. **Add your code** in a `code/` folder (datasets are git repos, so code uploads like any other file).
5. **Add your curated data** in a `data/` folder: the data your code reads, as you prepared it (e.g., your processed version of the challenge data, and any external data you added). Your code and data together should reproduce your `submission.csv`. Describe each file (source, license, preparation) in the data card, `data/README.md` (the template includes one). If a source is too large or its license does not allow copying, list it there with its exact version and how to download it.
6. **Make the dataset public** and paste its link, e.g. `https://huggingface.co/datasets/your-name/your-dataset`, in the **Submission** tab.

When you submit, the Space checks that the dataset is public, contains `submission.csv` and `README.md`, and that `submission.csv` has a number for every one of the 5,880 rows; it then records its current version (commit). You can update your dataset and submit again until the deadline, **up to 10 times a day** per team; **the version recorded at your latest submission counts**, so submit again after every change you want judged. Wait a few hours for your submission to appear on the leaderboard.

### Forecast file format

`submission.csv`, 4 columns, one row per city × year × metric:

```csv
city_id,year,metric,predicted_value
USW00094823,2019,annual_avg_temp,52.4
USW00094823,2019,total_precip_in,38.2
USW00094823,2019,hottest_day_temp,91.0
USW00094823,2019,cdd,845.0
USW00094823,2020,annual_avg_temp,53.1
...
USW00024233,2025,cdd,310.0
```

- **`city_id`:** the station `ID` from `city_info` (e.g., Pittsburgh = `USW00094823`, Seattle = `USW00024233`).
- **Total rows:** 210 cities × 7 years × 4 metrics = **5,880 rows**.

## Starter code

A working model in under 30 lines (scikit-learn):

```python
import pandas as pd
import numpy as np
from datasets import load_dataset
from sklearn.ensemble import RandomForestRegressor

# 1. Load the yearly data (up to 2018)
ds = load_dataset("CMU-OSPO/protostar-climate-train-to-2018", "annual_indices")
train_df = ds["train"].to_pandas()

# Metric codes and their columns in annual_indices:
# annual_avg_temp = "Avg Temp", total_precip_in = "ToT Prcp",
# hottest_day_temp = "Max Tmax", cdd = "cdd"
target = "Avg Temp"

# 2. Build lag features: each city's value 1, 2 and 3 rows (years) earlier
train_df = train_df.sort_values(["ID", "Year"])
for k in (1, 2, 3):
    train_df[f"lag_{k}"] = train_df.groupby("ID")[target].shift(k)
features = ["lag_1", "lag_2", "lag_3"]
fit_df = train_df.dropna(subset=features + [target])

model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(fit_df[features], fit_df[target])

# 3. Predict 2019-2025 iteratively
# ... generate predictions and save to submission.csv

# 4. Check your error locally against validation years:
def compute_mae(actual, predicted):
    return np.mean(np.abs(actual - predicted))
```

## FAQ

**Can I use data other than the challenge dataset?**
Yes, with one line drawn by *use*. Your **forecasts** may use weather records up to 2018-12-31, and data from any year that does not respond to the weather. After 2018, anything that responds to the weather gives away the answers, even when it is not weather data. The same data is welcome in your **analysis and policy idea**, where real impacts are exactly what a policy targets.

| Data (2019–2025) | Why it gives away the weather | Leaks | Forecast input? | Analysis / policy? |
|---|---|---|---|---|
| Temperature or rain from any source (NOAA, weather sites, ERA5 reanalysis, satellites) | It *is* the answer | All four metrics | ❌ | ✅ |
| Baseball home runs per game | Hot air is thinner, so balls fly farther (Callahan et al., 2023, *BAMS*, doi:10.1175/BAMS-D-22-0235.1) | Hottest day, CDD | ❌ | ✅ |
| River streamflow (USGS) | Rain becomes runoff within days | Precipitation | ❌ | ✅ |
| Ozone exceedance days (EPA) | Ozone forms faster in heat and sun | Hottest day, CDD | ❌ | ✅ |
| Spring leaf-out and bloom dates (USA-NPN) | Plants respond to accumulated warmth | Average temperature | ❌ | ✅ |
| West Nile virus cases (CDC) | Mosquitoes multiply faster in heat | CDD | ❌ | ✅ |
| Electricity demand (EIA), searches for "AC repair" | Air conditioning drives summer peaks | CDD | ❌ | ✅ |
| Census, land cover, tree canopy, building stock | Does not respond to the year's weather | — | ✅ | ✅ |
| Weather records **up to 2018** from other sources | Same cutoff as the challenge dataset | — | ✅ | ✅ |

When in doubt: if a 2019–2025 series would be different in a hotter or wetter year, keep it out of your forecasts. List every external source in your README.

**Can I score my own forecasts against 2019–2025 observations?**
The observations are public, so you could, but choosing a model by its score on them uses the answers, even if they never enter the model.

| Use | Allowed? | Why |
|---|---|---|
| Scoring model variants on 2019–2025 observations to choose or tune one | ❌ | Selecting by the answers uses them |
| Scoring a frozen, committed forecast afterwards, for analysis | ✅ | The forecast is fixed; declare it in your README with the commit hash |

**Can I use LLMs (e.g., ChatGPT, Claude, Copilot) or pretrained forecasting models?**
Yes, as tools, not as a source of answers. A model trained on data from after 2018 has already "seen" how 2019–2025 turned out, so the numbers it gives can carry the answers even if you never mention those years.

| Use | Forecast input? | Why |
|---|---|---|
| An LLM writes, debugs or explains your code | ✅ | The numbers still come from your data and your model |
| An LLM helps you brainstorm methods or features, or edit your README | ✅ | It shapes your method, not your values |
| An LLM gives you values (e.g., "What was Phoenix's CDD in 2021?", "Predict Pittsburgh's 2023 average temperature") | ❌ | Its training data includes the 2019–2025 weather |
| An LLM fills in or "corrects" `predicted_value` | ❌ | Same reason, even if your model produced the first draft |
| A pretrained time-series model (e.g., Chronos, TimesFM, Moirai) whose training data stops before 2019 | ✅ | Declare its name, version and training-data cutoff in your README |
| A pretrained model whose training data includes data from 2019 onward, or whose training data is unknown | ❌ | It may have learned the answers; check the model card first |
| AI weather or climate models (e.g., GraphCast, Pangu-Weather) trained on reanalysis from 2019 onward | ❌ | Reanalysis after 2018 *is* weather observations |

Using an LLM in your **analysis and policy idea** is welcome: for example, to summarize heat-adaptation literature or to explore 2019–2025 impacts. **Say in your README which AI tools you used and for what.** When unsure whether a model learned from data after 2018, keep it out of your forecasts or ask in the Space's [Community tab](https://huggingface.co/spaces/CMU-OSPO/protostar-challenge-climate-risk-intelligence/discussions).

## 🤖 AI agents: allowed, with guardrails

> **The use of AI agents is allowed.** Agents can write code, run experiments and help document your work. Set them up so they cannot fetch 2019–2025 weather (see below), and say how you used them in your README. See the [LLM Documentation Guide](https://guides.library.cmu.edu/LLMDocumentationGuide) (CMU Libraries) for ideas on how to document your LLM and agent use.

**Can we use AI agents (e.g., Claude Code, Codex, Cursor)?**
Yes: for data preparation, modeling, experiments, your README and your data card. The same line applies as for LLMs: an agent can build your method, but it cannot be the source of 2019–2025 values.

**How do we stop an agent from leaking 2019–2025 data?**
Agents search the web, call APIs and download files on their own, so set them up so they cannot fetch the answers:

- Put the data rule in the agent's instructions file (e.g., `AGENTS.md` or `CLAUDE.md`; the template includes one): only weather data up to 2018-12-31.
- Cap every weather download at that end date (e.g., NOAA, Meteostat, Open-Meteo, ERA5).
- Add a check to your code that stops if any weather input is dated after 2018.
- Review what the agent downloaded. If it fetched weather from 2019 onward, keep it out of your forecasts.

**How do we document agent use?**
In your README's *AI Tools and Agents* section: the tool, the model, the tasks it did, and what a person reviewed. Keep the agent's instructions file in `code/`. Your code must reproduce `submission.csv` **without** the agent.

**Can an agent use our Hugging Face token or submit for us?**
An agent can push to your dataset with a **fine-grained token** limited to that one repository. Never commit tokens to your dataset. Submitting in the *Submission* tab is done by a registered team member, signed in with Hugging Face.

**Does agent use affect judging?**
It is not penalized. Friction your agent ran into (missing metadata, unclear licenses, broken APIs) is good material for your **Feedback to the Ecosystem**. Values produced by an AI model that learned from later data break the data rule, disclosed or not.

## Credits

Please cite the data you use (and list any external data in your README):

- Lai, Yuchuan; Dzombak, David (2019). Compiled historical daily temperature and precipitation data for selected 210 U.S. cities. Carnegie Mellon University. https://doi.org/10.1184/R1/7890488.v6
- Lai, Yuchuan; Dzombak, David (2019). Historical changes of annual temperature and precipitation indices at selected 210 U.S. cities. Carnegie Mellon University. https://doi.org/10.1184/R1/7961012.v6
- Lai, Y., & Dzombak, D. A. (2019). Use of historical data to assess regional climate change. *Journal of Climate*, 32(14), 4299–4320. https://doi.org/10.1175/JCLI-D-18-0630.1

---

# 3. Registration tab (`tabs/registration.py`)

Summarized from the tab's code (the live tab needs a Hugging Face sign-in).

- **My team** panel: shows your team once you are in one. "Leaving the team removes you from it. If you are the last member, the team is deleted, with its submissions." Button: Leave team.
- **Register** form (shown when you are not in a team): each participant can be in one team only, with at most 5 members. One person creates the team and gets a **join code**; teammates choose *Join an existing team* and enter the team name and that code. Name and e-mail are only visible to the organisers.
- Fields: Full name, E-mail, Affiliation, Team name, Join code (only when joining). Mode: *Create a new team* or *Join an existing team*.
- Requires signing in with Hugging Face.

# 4. Submission tab (`tabs/submission.py`)

- Heading: **Submit**.
- You must be signed in and in a team. Your submission is the link to your team's **public Hugging Face dataset**, containing `submission.csv` (forecasts), `README.md` (method, policy idea, feedback to the ecosystem) and your code in `code/`.
- The current version (commit) of your dataset is recorded on submit. You can submit again until the deadline, up to 10 per team per day (the day resets at 7 PM ET). **Only your team's latest submission counts**, at the version recorded then.
- Wait **a few hours** for your submission to appear on the leaderboard.
- Input: "Link to your Hugging Face dataset" (placeholder `https://huggingface.co/datasets/your-name/your-dataset`). Button: Submit. Below it, a table of "Your team's submissions".

# 5. Leaderboard and Judging tabs

- **Leaderboard** (`tabs/leaderboard.py`): live scores (2019–2021) for teams plus the three baselines; final scores (2022–2025) become visible after the deadline. Not captured here, because it is dynamic and needs the running app.
- **Judging** (`tabs/judging.py`): restricted to judges listed in the Space config. Not captured.

# 6. Key config values (`config.py`)

| Setting | Value |
|---|---|
| Challenge name | Protostar Challenge: Climate Risk Intelligence |
| Organization | CMU-OSPO |
| Challenge start | 2026-11-02 00:00 ET |
| Deadline | 2026-11-10 23:59 ET |
| Live years | 2019–2021 |
| Final years | 2022–2025 |
| Metrics | annual_avg_temp, total_precip_in, hottest_day_temp, cdd |
| Submission files checked | submission.csv, README.md (max 5 MB each) |
| Max submissions per team per day | 10 (UTC day, resets 7 PM ET) |
| Max team size | 5 |
| Scoring interval | every 6 hours |
| Answer key repo (private) | CMU-OSPO/protostar-climate-ground-truth, file `answer_key.csv`, scored rows only |
| Training data repo | CMU-OSPO/protostar-climate-train-to-2018 |
| Judges' score scale | 1 to 5 per criterion |

# 7. Repo layout (Files tab)

Top level: `assets/`, `content/` (about.md, data.md), `data/`, `tabs/` (about.py, data.py, judging.py, leaderboard.py, registration.py, submission.py), `.gitignore`, `LICENSE`, `README.md`, `app.py`, `config.py`, `icons.py`, `requirements.txt`, `style.css`, `theme.py`, `utils.py`.
Duplicated from `EmmaScharfmann/challenge-template`.
