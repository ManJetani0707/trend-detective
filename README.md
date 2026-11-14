---
title: Trend Detective
emoji: 🔎
colorFrom: blue
colorTo: red
sdk: docker
app_port: 8501
pinned: false
---

# 🔎 Trend Detective (NASA Space Apps 2026: Be An Earth System Trend Detective)

Pick a NASA Earth-science variable and a region. See the monthly time series, how fast it is changing
per decade, where it is changing (optional map), and whether the change is statistically significant.

## Variables (7 working, 2 planned)
| Variable | NASA product | Status |
|---|---|---|
| Air temperature 2 m | MERRA-2 M2TMNXSLV v5.12.4 (T2M) | ready, verified |
| Total water vapour | MERRA-2 M2TMNXSLV (TQV) | ready, verified live |
| Total column ozone | MERRA-2 M2TMNXSLV (TO3) | ready, verified |
| Rainfall | GPM IMERG GPM_3IMERGM v07 (precipitation) | ready, verified live |
| Soil moisture 0-10 cm | GLDAS_NOAH025_M v2.1 | ready, verified |
| Root-zone soil moisture | GLDAS_NOAH025_M v2.1 | ready, verified |
| Land skin temperature | GLDAS_NOAH025_M v2.1 | ready, verified |
| NDVI | MODIS MOD13C2 v061 | planned (HDF4 reader needed) |
| NO2 | OMI OMNO2d (daily) | planned (daily-to-monthly step needed) |

Exact status notes live in `src/config.py` (`check` field).

## Setup (local)
```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt     # only needed to run the tests
export EARTHDATA_TOKEN="<your NEW token>"             # Windows PowerShell: $env:EARTHDATA_TOKEN="..."
python scripts/build_demo_cache.py                    # once; downloads the 3 demo boxes (takes a while)
streamlit run app.py
```
Get a token: urs.earthdata.nasa.gov -> log in -> **Generate Token**. Never paste it into code, chat or GitHub.

## Deploy on Hugging Face Spaces
Hugging Face removed the built-in Streamlit option (April 2025), so this project uses the **Docker** SDK
with the included `Dockerfile` (front matter above: `sdk: docker`, `app_port: 8501`).
1. huggingface.co -> New Space -> SDK **Docker** (blank template) -> Public -> CPU Basic (free).
2. Files tab -> Add file -> Upload files: `Dockerfile`, `README.md`, `app.py`, `requirements.txt`, and the folders
   `src`, `data` (with the `.nc` demo files) and `.streamlit`. Do NOT upload `.venv` or `.td_cache`.
3. Settings -> Variables and secrets -> new **secret** `EARTHDATA_TOKEN` (needed only for live searches).
4. Wait for "Building" then "Running". Demos work without any login.
Fallback if Docker is unavailable on your account: Streamlit Community Cloud (share.streamlit.io) from a GitHub repo.

## How it works
`data.py` (cache -> earthaccess -> NASA POWER) -> `processing.py` (clip, mask, cos-lat mean, anomalies) ->
`stats.py` (Theil-Sen, Mann-Kendall, OLS 95% CI, verdict) -> `plots.py` (Plotly) -> `app.py` (Streamlit).

## Honest limits
- Linear trends only; non-linear trends are future work.
- Mann-Kendall assumes independent points; monthly anomalies are correlated, so the verdict card also shows a
  Hamed-Rao check and warns on disagreement.
- 10-25 years can reflect natural variability, not only climate change.
- MERRA-2 and GLDAS are model/reanalysis products. POWER fallback is one point at the box centre.
- Demo regions and years in `config.py` are **suggestions** until your team confirms them.

## Sources and credits
NASA GES DISC (MERRA-2, GPM IMERG, GLDAS, OMI), NASA LP DAAC (MODIS), NASA POWER; open-source: earthaccess,
xarray, SciPy, pymannkendall, Plotly, Streamlit. No code was copied from other projects.
Cite each dataset's DOI from its Earthdata catalog page when you present.

## AI assistance disclosure (Super Intelligence use)
- **Code:** the Python code in this repository was generated with AI assistance (Claude by Anthropic) and was then run,
  tested (automated tests) and reviewed by Team Radiant Orbit. Each source file carries this note in its header.
- **Presentation:** AI assistants (Claude and Gemini) helped with slide wording and formatting.
- **Data and results:** all NASA data downloads and all statistical results shown in the app and slides were produced by
  running the code on real NASA data; no data was invented by an AI. Synthetic data appears only inside automated tests
  and is labelled as such.
