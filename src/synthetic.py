"""SYNTHETIC (FAKE) DATA: for unit tests and UI development ONLY.

Nothing here is NASA data. The app only uses it when the environment variable
TD_DEV_SYNTHETIC=1 is set, and then shows a loud warning banner.

Original code written for NASA Space Apps 2026.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import xarray as xr


def synthetic_cube(trend_per_decade: float = 0.3, years=(2001, 2025), bbox=(68.0, 20.0, 75.0, 25.0),
                   step: float = 0.5, noise: float = 0.4, seed: int = 0, base: float = 25.0,
                   seasonal_amp: float = 6.0) -> xr.DataArray:
    """Seasonal cycle + known linear trend + noise on a lat/lon grid."""
    rng = np.random.default_rng(seed)
    w, s, e, n = bbox
    lat = np.arange(s, n + 1e-9, step)
    lon = np.arange(w, e + 1e-9, step)
    time = pd.date_range(f"{years[0]}-01-01", f"{years[1]}-12-01", freq="MS")
    t_years = np.arange(len(time)) / 12.0
    season = seasonal_amp * np.sin(2 * np.pi * (time.month.to_numpy() - 4) / 12.0)
    series = base + season + (trend_per_decade / 10.0) * t_years
    data = series[:, None, None] + rng.normal(0, noise, size=(len(time), len(lat), len(lon)))
    return xr.DataArray(data, coords={"time": time, "lat": lat, "lon": lon}, dims=("time", "lat", "lon"),
                        name="synthetic", attrs={"source": "SYNTHETIC TEST DATA (not NASA data)", "already_converted": True})
