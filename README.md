---
title: Trend Detective
emoji: 🔎
colorFrom: blue
colorTo: red
sdk: streamlit
sdk_version: 1.40.0
app_file: app.py
pinned: false
---

# 🔎 Trend Detective (NASA Space Apps 2026: Be An Earth System Trend Detective)

Pick a NASA Earth-science variable and a region. See the monthly time series, how fast it is changing
per decade, where it is changing (optional map), and whether the change is statistically significant.

## Variables (8 working paths, 2 planned)
| Variable | NASA product | Status |
|---|---|---|
| Air temperature 2 m | MERRA-2 M2TMNXSLV v5.12.4 (T2M) | ready, verified |
| Total water vapour | MERRA-2 M2TMNXSLV (TQV) | ready, **verify TQV name on first run** |
| Total column ozone | MERRA-2 M2TMNXSLV (TO3) | ready, verified |
| Rainfall | GPM IMERG GPM_3IMERGM v07 (precipitation) | ready, **verify HDF5 group `Grid`** |
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
export EARTHDATA_TOKEN="<your NEW token>"             # Windows PowerShell: $env:EARTHDATA_TOKEN="..."
python scripts/build_demo_cache.py                    # once; downloads the 3 demo boxes (takes a while)
streamlit run app.py
```
Get a token: urs.earthdata.nasa.gov -> log in -> **Generate Token**. Never paste it into code, chat or GitHub.

## Deploy on Hugging Face Spaces
1. huggingface.co -> New Space -> SDK **Streamlit** -> name it.
2. Push this folder (the README front matter above is already the Space config). Commit `data/demo_cache/*.nc`.
3. Space -> Settings -> **Variables and secrets** -> new **secret** `EARTHDATA_TOKEN`.
4. Demos work without a login. Guided mode needs the secret for downloads.

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
xarray, SciPy, pymannkendall, Plotly, Streamlit. All code here is original; no snippets were copied.
Cite each dataset's DOI from its Earthdata catalog page when you present.
