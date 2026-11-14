"""Catalog of NASA variables and demo examples for Trend Detective.

Everything here was checked against NASA pages on 2026-11-13 EXCEPT the items
whose `check` text says "VERIFY". Those are marked so nobody trusts them blindly.

Original code written for NASA Space Apps 2026.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

BBox = Tuple[float, float, float, float]  # (west, south, east, north), degrees


@dataclass(frozen=True)
class Variable:
    key: str
    topic: str                 # shown in the guided Q&A
    label: str
    definition: str            # one plain-language line
    short_name: str            # earthaccess / CMR collection short name
    version: str
    var_names: Tuple[str, ...]  # candidate variable names inside the file (first match wins)
    group: Optional[str]       # HDF5 group to open (None = root)
    units: str                 # units AFTER transform
    transform: str             # "none" | "K_to_C" | "mmhr_to_mmday"
    first_year: int
    power_param: Optional[str]  # NASA POWER monthly parameter, None = no fallback
    status: str                # "ready" (code path implemented) | "planned"
    check: str                 # what is verified and what is not


VARIABLES = {
    v.key: v
    for v in [
        Variable(
            key="merra2_t2m", topic="Temperature", label="Air temperature at 2 m (MERRA-2)",
            definition="How warm the air is about 2 metres above the ground, from NASA's MERRA-2 reanalysis.",
            short_name="M2TMNXSLV", version="5.12.4", var_names=("T2M",), group=None,
            units="°C", transform="K_to_C", first_year=1980, power_param="T2M", status="ready",
            check="Verified: collection M2TMNXSLV v5.12.4, variable T2M (K), 0.625x0.5 deg, 1980-present.",
        ),
        Variable(
            key="merra2_tqv", topic="Atmosphere (moisture)", label="Total water vapour in the air column (MERRA-2)",
            definition="All the water vapour in a column of air from the ground to space; more vapour means a moister atmosphere.",
            short_name="M2TMNXSLV", version="5.12.4", var_names=("TQV",), group=None,
            units="kg m⁻²", transform="none", first_year=1980, power_param=None, status="ready",
            check="VERIFY: collection page says it holds total precipitable water vapour, and TQV is listed "
                  "for the hourly sibling M2T1NXSLV. Confirm TQV exists in the monthly file on first run.",
        ),
        Variable(
            key="merra2_to3", topic="Ozone", label="Total column ozone (MERRA-2)",
            definition="The thickness of the ozone layer above a spot, in Dobson Units (more = thicker shield against UV).",
            short_name="M2TMNXSLV", version="5.12.4", var_names=("TO3",), group=None,
            units="Dobson Units", transform="none", first_year=1980, power_param=None, status="ready",
            check="Verified: TO3 (Dobsons) is listed in the M2TMNXSLV variable table. "
                  "This is a reanalysis value, not a raw satellite retrieval.",
        ),
        Variable(
            key="gpm_precip", topic="Rainfall", label="Rainfall rate (GPM IMERG, monthly)",
            definition="Average rain rate seen by satellites and corrected with rain gauges, shown here in mm per day.",
            short_name="GPM_3IMERGM", version="07", var_names=("precipitation",), group="Grid",
            units="mm/day", transform="mmhr_to_mmday", first_year=2001, power_param="PRECTOTCORR", status="ready",
            check="Verified: GPM_3IMERGM v07, variable `precipitation` in mm/hr, 0.1 deg. "
                  "VERIFY: that the HDF5 group is named `Grid` (the code also tries the root group).",
        ),
        Variable(
            key="gldas_soil_top", topic="Soil moisture", label="Soil moisture, top 10 cm (GLDAS)",
            definition="How much water sits in the top 10 cm of soil, from a NASA land-surface model (not a direct measurement).",
            short_name="GLDAS_NOAH025_M", version="2.1", var_names=("SoilMoi0_10cm_inst",), group=None,
            units="kg m⁻²", transform="none", first_year=2000, power_param=None, status="ready",
            check="Verified: GLDAS_NOAH025_M v2.1, SoilMoi0_10cm_inst (kg m-2). Coverage is 60S-90N only.",
        ),
        Variable(
            key="gldas_root", topic="Soil moisture", label="Root-zone soil moisture (GLDAS)",
            definition="Water available to plant roots in the soil, from a NASA land-surface model.",
            short_name="GLDAS_NOAH025_M", version="2.1", var_names=("RootMoist_inst",), group=None,
            units="kg m⁻²", transform="none", first_year=2000, power_param=None, status="ready",
            check="Verified: RootMoist_inst (kg m-2) is in the GLDAS_NOAH025_M v2.1 variable table.",
        ),
        Variable(
            key="gldas_skin", topic="Temperature", label="Land surface (skin) temperature (GLDAS)",
            definition="How hot the ground surface itself is, which can differ a lot from the air temperature.",
            short_name="GLDAS_NOAH025_M", version="2.1", var_names=("AvgSurfT_inst",), group=None,
            units="°C", transform="K_to_C", first_year=2000, power_param=None, status="ready",
            check="Verified: AvgSurfT_inst (K) is in the GLDAS_NOAH025_M v2.1 variable table.",
        ),
        Variable(
            key="modis_ndvi", topic="Vegetation", label="Vegetation greenness NDVI (MODIS Terra)",
            definition="A 0-to-1 'greenness' score: higher means denser, healthier plants.",
            short_name="MOD13C2", version="061", var_names=("CMG 0.05 Deg Monthly NDVI",), group=None,
            units="NDVI", transform="none", first_year=2001, power_param=None, status="planned",
            check="Verified: MOD13C2 v061 (monthly, 0.05 deg CMG, NDVI + EVI layers). VERIFY exact layer name. "
                  "PLANNED: files are HDF4-EOS, which xarray cannot read directly (needs GDAL/pyhdf). Stretch goal.",
        ),
        Variable(
            key="omi_no2", topic="Air quality", label="Tropospheric nitrogen dioxide (OMI)",
            definition="Nitrogen dioxide pollution in the lower atmosphere, mostly from burning fuel; more means dirtier air.",
            short_name="OMNO2d", version="003", var_names=("ColumnAmountNO2TropCloudScreened",), group=None,
            units="molecules cm⁻²", transform="none", first_year=2005, power_param=None, status="planned",
            check="Verified: OMNO2d is a DAILY 0.25 deg product (v003; a v004 page also exists, VERIFY which to use). "
                  "PLANNED: needs daily-to-monthly averaging of HDF-EOS5 files. Stretch goal.",
        ),
    ]
}

TOPICS = sorted({v.topic for v in VARIABLES.values()})

# ---------------------------------------------------------------------------
# Region presets and demos.
# SUGGESTED values, written by the assistant: NOT yet confirmed by the team.
# Confirm or replace each box at https://bboxfinder.com (format: west,south,east,north).
# ---------------------------------------------------------------------------
REGION_PRESETS: dict[str, BBox] = {
    "Gujarat, India (suggested box)": (68.1, 20.1, 74.5, 24.7),
    "Amazon basin (suggested box)": (-70.0, -12.0, -50.0, 0.0),
    "Sahel, Africa (suggested box)": (-15.0, 11.0, 15.0, 17.0),
}

DEMOS = {
    "demo_gujarat_temp": dict(
        title="Is Gujarat getting warmer?", var="merra2_t2m",
        region="Gujarat, India (suggested box)", bbox=REGION_PRESETS["Gujarat, India (suggested box)"],
        years=(1990, 2025), confirmed=False),
    "demo_gujarat_rain": dict(
        title="Is Gujarat getting wetter?", var="gpm_precip",
        region="Gujarat, India (suggested box)", bbox=REGION_PRESETS["Gujarat, India (suggested box)"],
        years=(2001, 2025), confirmed=False),
    "demo_amazon_soil": dict(
        title="Is the Amazon soil drying?", var="gldas_soil_top",
        region="Amazon basin (suggested box)", bbox=REGION_PRESETS["Amazon basin (suggested box)"],
        years=(2001, 2025), confirmed=False),
}

DEFAULT_YEARS = (2001, 2025)
MIN_MONTHS = 60   # refuse to run statistics on fewer than 5 years of monthly data
ALPHA = 0.05
