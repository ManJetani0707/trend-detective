"""Trend Detective: a Streamlit app for NASA Space Apps 2026 'Be An Earth System Trend Detective'.

Run:  streamlit run app.py
Original code written for NASA Space Apps 2026.
"""
from __future__ import annotations

import os

import streamlit as st

from src.config import ALPHA, DEFAULT_YEARS, DEMOS, REGION_PRESETS, TOPICS, VARIABLES
from src.data import DataUnavailable, demo_available, get_cube, load_demo
from src.plots import seasonal_figure, timeseries_figure, trend_map_figure, verdict_card_html
from src.processing import RecordTooShort, build_series, pixel_anomaly_cube
from src.stats import analyze_trend, pixel_trends, verdict

st.set_page_config(page_title="Trend Detective", page_icon="🔎", layout="wide")

DEV_SYNTHETIC = os.environ.get("TD_DEV_SYNTHETIC") == "1"


def _synthetic_cube(bbox, years):
    from src.synthetic import synthetic_cube
    return synthetic_cube(bbox=bbox, years=years)

def show_results(cube, var, bbox, region_name: str, want_map: bool):
    """Process -> statistics -> visuals. Shared by guided mode and demos."""
    try:
        out = build_series(cube, bbox, var)
        res = analyze_trend(out["anomalies"])
    except RecordTooShort as exc:
        st.warning(str(exc))
        return
    except ValueError as exc:
        st.error(str(exc))
        return

    source = cube.attrs.get("source", "unknown")
    v = verdict(res, var.units, var.label)
    for note in out["notes"]:
        st.info(note)
    st.markdown(verdict_card_html(v, res, var.units, region_name, source), unsafe_allow_html=True)
    st.plotly_chart(timeseries_figure(out["anomalies"], res, var.units, f"{var.label}: monthly anomalies"), width="stretch")
    with st.expander("What am I looking at? (plain language)"):
        st.markdown(
            f"- **Anomaly** = this month's value minus the usual value for that calendar month, so seasons do not hide the trend.\n"
            f"- **Theil-Sen slope** is a robust 'typical slope'; one odd month will not drag it around.\n"
            f"- **Mann-Kendall p-value** asks: if there were really no trend, how likely is a pattern this strong? "
            f"Below {ALPHA} we call it significant.\n"
            f"- **OLS cross-check** is the ordinary straight-line fit; if it agrees, we trust the answer more.\n"
            f"- Only **straight-line** trends are tested here. Curved or sudden changes are future work.\n"
            f"- Averaged over **{out['n_cells']}** grid cell(s), weighted by cos(latitude).")

    st.plotly_chart(seasonal_figure(out["climatology"], var.units), width="stretch")

    if want_map:
        if out["n_cells"] < 2:
            st.info("The map needs at least 2 grid cells; choose a bigger box.")
            return
        with st.spinner("Testing every grid cell (this can take a few seconds)..."):
            slope, pval, stride = pixel_trends(pixel_anomaly_cube(out["clipped"]))
        if stride > 1:
            st.caption(f"Box is large, so every {stride}th grid cell is shown to keep the app fast.")
        st.plotly_chart(trend_map_figure(slope, pval, var.units), width="stretch")


st.title("🔎 Trend Detective")
st.caption("Pick a NASA Earth-science variable and a region. We show what is changing, where, by how much, "
           "and whether the change is statistically significant.")

if DEV_SYNTHETIC:
    st.error("DEV MODE: synthetic (fake) data is switched on. Nothing shown here is real NASA data.")

tab_guided, tab_demo, tab_about = st.tabs(["🧭 Guided Q&A", "⚡ Instant demos", "ℹ️ Sources & limits"])

# ------------------------------------------------------------------ guided mode
with tab_guided:
    st.subheader("Step 1: What do you want to investigate?")
    ready_topics = [t for t in TOPICS if any(v.topic == t and v.status == "ready" for v in VARIABLES.values())]
    topic_list = ready_topics + [t for t in TOPICS if t not in ready_topics]   # working topics first
    topic = st.selectbox("Topic", topic_list, key="topic")
    options = sorted((v for v in VARIABLES.values() if v.topic == topic), key=lambda v: v.status != "ready")
    labels = {v.label + ("  (coming soon)" if v.status != "ready" else ""): v for v in options}
    choice = st.selectbox("Variable", list(labels), key="variable")
    var = labels[choice]
    st.markdown(f"**In one line:** {var.definition}")
    if var.status != "ready":
        st.warning("This variable is a planned stretch goal and is not implemented yet. Pick another one.")

    st.subheader("Step 2: Where?")
    preset = st.selectbox("Region", list(REGION_PRESETS) + ["Custom box"], key="region")
    if preset == "Custom box":
        c1, c2, c3, c4 = st.columns(4)
        w = c1.number_input("West °", -180.0, 180.0, 68.1)
        s = c2.number_input("South °", -90.0, 90.0, 20.1)
        e = c3.number_input("East °", -180.0, 180.0, 74.5)
        n = c4.number_input("North °", -90.0, 90.0, 24.7)
        bbox = (w, s, e, n)
        region_name = f"Custom box ({w:g}, {s:g}, {e:g}, {n:g})"
        st.caption("Tip: draw a box at bboxfinder.com and copy the west, south, east, north values.")
    else:
        bbox = REGION_PRESETS[preset]
        region_name = preset
        st.caption(f"Box (west, south, east, north): {bbox}")

    st.subheader("Step 3: Which years?")
    lo = max(var.first_year, 1980)
    y0, y1 = st.slider("Years", lo, 2025, (max(lo, DEFAULT_YEARS[0]), 2025), key="years")
    want_map = st.checkbox("Also draw the per-pixel trend map (slower)", value=False)

    if st.button("🔎 Investigate", type="primary", disabled=var.status != "ready"):
        try:
            with st.spinner("Getting NASA data (first time can take a few minutes; later runs use the cache)..."):
                cube = _synthetic_cube(bbox, (y0, y1)) if DEV_SYNTHETIC else get_cube(var, bbox, y0, y1)
            show_results(cube, var, bbox, region_name, want_map)
        except DataUnavailable as exc:
            st.error(f"Could not get data. {exc}")

# ------------------------------------------------------------------ demos
with tab_demo:
    st.subheader("Instant examples")
    st.caption("These load from files saved inside the app, so no login or waiting is needed.")
    for demo_id, d in DEMOS.items():
        ready = demo_available(demo_id) or DEV_SYNTHETIC
        label = f"{d['title']}" + ("" if ready else "  (cache not built yet)")
        if st.button(label, key=demo_id, disabled=not ready):
            dvar = VARIABLES[d["var"]]
            try:
                cube = _synthetic_cube(d["bbox"], d["years"]) if DEV_SYNTHETIC else load_demo(demo_id)
                if not d.get("confirmed"):
                    st.caption("Region and years for this demo are suggested defaults still waiting for team confirmation.")
                show_results(cube, dvar, d["bbox"], d["region"], want_map=False)
            except DataUnavailable as exc:
                st.error(str(exc))

# ------------------------------------------------------------------ about
with tab_about:
    st.markdown("""
**Data sources (all free, open NASA data):** MERRA-2 (GES DISC), GPM IMERG (GES DISC), GLDAS Noah (GES DISC),
NASA POWER (fallback). Planned: MODIS MOD13C2 NDVI (LP DAAC), OMI NO2 (GES DISC).

**Method:** clip to box, mask missing values, cos(latitude)-weighted average, remove the seasonal cycle,
then Theil-Sen slope + Mann-Kendall test (pymannkendall), cross-checked with OLS and a 95% confidence interval.

**Verdict rule:** p < 0.05 means "significant rising/falling trend"; otherwise "visible but not yet significant".

**Limits you should know:**
- Only straight-line trends are tested. Non-linear trends are future work.
- Monthly values in the same series are correlated, which can make Mann-Kendall over-confident;
  the verdict card warns you when an autocorrelation-aware check disagrees.
- A trend over 10 to 25 years can be natural variability (for example El Niño), not long-term climate change.
- GLDAS and MERRA-2 are model/reanalysis products, not direct measurements.
- NASA POWER fallback is a single point at the centre of your box, so it can differ from the area average.
""")
