# 🌎 Gujarat Earth System Trend Detective
### NASA Space Apps Challenge 2026 — "Be An Earth System Trend Detective"

A live, interactive web application that empowers regional planners, agricultural scientists, and emergency responders to detect and evaluate multi-decadal climatic shifts in Gujarat, India.

🔗 **Live Application URL:** [https://manjetani0707-trend-detective.streamlit.app/](https://manjetani0707-trend-detective.streamlit.app/)

---

## 🎯 Key Features
1. **Interactive Guided Mode:** Instantly map curated variables (Temperature, Rainfall, Soil Moisture) to plain-language definitions.
2. **Scientific NetCDF Pipeline:** Ingests high-cadence `.nc` datasets using `xarray` and calculates monthly climatological anomalies to strip away seasonal cycles.
3. **Rigorous Statistical Verification:**
   * **Mann-Kendall Test:** Calculates non-parametric trend significance ($p < 0.05$).
   * **Theil-Sen Slope Estimator:** Quantifies the robust rate of change (units per decade).
   * **OLS Regression:** Cross-checks trajectories with 95% Confidence Intervals.
4. **Interactive Plotly Visualizations:** Clear, responsive graphs displaying anomaly trends, confidence intervals, and instant data exports.
5. **Instant Preloaded Demos:** Zero-friction demonstrations for Gujarat temperature, rainfall, and soil moisture running instantly from optimized cached data.

---

## 📁 Repository Structure
```text
trend-detective/
├── .streamlit/
│   └── config.toml          # Streamlit UI theme configurations
├── data/
│   └── demo_cache/
│       ├── demo_gujarat_temp.nc  # 100% Downloaded Cache (0.19 MB)
│       ├── demo_gujarat_rain.nc  # 100% Downloaded Cache (1.37 MB)
│       └── demo_amazon_soil.nc   # 100% Downloaded Cache (4.17 MB)
├── src/
│   ├── config.py            # Global variables and spatial coordinates
│   ├── data.py              # Ingestion & processing core
│   ├── stats.py             # Mann-Kendall and OLS Engines
│   └── plots.py             # Plotly graph configurations
├── app.py                   # Streamlit Frontend Entry Point
├── requirements.txt         # Core dependencies
└── README.md                # Submission Documentation
