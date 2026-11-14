"""Processing: clip -> mask missing -> latitude-weighted mean -> monthly anomalies.

Original code written for NASA Space Apps 2026.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import xarray as xr

from .config import BBox, MIN_MONTHS, Variable


class RecordTooShort(ValueError):
    """Raised when there is not enough monthly data for honest statistics."""


def apply_transform(da: xr.DataArray, transform: str) -> xr.DataArray:
    if da.attrs.get("already_converted"):
        return da
    if transform == "K_to_C":
        return da - 273.15
    if transform == "mmhr_to_mmday":
        return da * 24.0
    if transform == "none":
        return da
    raise ValueError(f"Unknown transform '{transform}'")


def mask_missing(da: xr.DataArray) -> xr.DataArray:
    """Turn fill values and absurd numbers into NaN (xarray already did _FillValue)."""
    return da.where(np.isfinite(da) & (da.__abs__() < 1e15) & (da != -9999))


def clip_region(da: xr.DataArray, bbox: BBox) -> xr.DataArray:
    """Keep grid cells whose centres lie inside the box.

    If the box is smaller than one grid cell, use the single nearest cell instead
    (the caller can see this through attrs['clip_note']).
    """
    w, s, e, n = bbox
    if not (w < e and s < n):
        raise ValueError("Bounding box must have west < east and south < north (boxes crossing 180° are not supported).")
    da = da.sortby("lat").sortby("lon")
    out = da.sel(lat=slice(s, n), lon=slice(w, e))
    if out.sizes["lat"] == 0 or out.sizes["lon"] == 0:
        out = da.sel(lat=[(s + n) / 2], lon=[(w + e) / 2], method="nearest")
        out.attrs["clip_note"] = "Box smaller than one grid cell: used the nearest cell."
    return out


def area_average(da: xr.DataArray) -> pd.Series:
    """Latitude-weighted (cos φ) mean over the box, ignoring NaN cells."""
    weights = np.cos(np.deg2rad(da["lat"]))
    mean = da.weighted(weights).mean(dim=("lat", "lon"), skipna=True)
    return mean.to_series().rename("value")


def monthly_anomalies(series: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Remove the seasonal cycle: subtract each calendar month's long-term mean.

    Returns (anomalies, climatology indexed 1..12).
    """
    s = series.copy()
    s.index = pd.DatetimeIndex(s.index).to_period("M").to_timestamp()
    s = s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="MS"))  # expose gaps
    valid = s.dropna()
    if len(valid) < MIN_MONTHS:
        raise RecordTooShort(
            f"Only {len(valid)} valid months found; at least {MIN_MONTHS} (5 years) are needed for a trend test. "
            "Pick a longer period or a different variable.")
    clim = valid.groupby(valid.index.month).mean()
    anom = s - s.index.month.map(clim).to_numpy()
    return anom.dropna().rename("anomaly"), clim


def prepare_cube(cube: xr.DataArray, bbox: BBox, var: Variable) -> xr.DataArray:
    """Convert units, mask, clip. Used by both the area average and the map."""
    return clip_region(mask_missing(apply_transform(cube, var.transform)), bbox)


def build_series(cube: xr.DataArray, bbox: BBox, var: Variable):
    """Full pipeline for one region. Returns dict with raw mean series, anomalies, climatology, notes."""
    clipped = prepare_cube(cube, bbox, var)
    raw = area_average(clipped)
    anom, clim = monthly_anomalies(raw)
    notes = []
    if clipped.attrs.get("clip_note"):
        notes.append(clipped.attrs["clip_note"])
    if cube.attrs.get("fallback_reason"):
        notes.append("NASA POWER fallback used (single point at the box centre): " + cube.attrs["fallback_reason"])
    return dict(raw=raw, anomalies=anom, climatology=clim, clipped=clipped, notes=notes,
                n_cells=int(clipped.sizes["lat"] * clipped.sizes["lon"]))


def pixel_anomaly_cube(clipped: xr.DataArray) -> xr.DataArray:
    """Per-pixel monthly anomalies (for the optional trend map)."""
    clim = clipped.groupby("time.month").mean("time", skipna=True)
    return clipped.groupby("time.month") - clim
