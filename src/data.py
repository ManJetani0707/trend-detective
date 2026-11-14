"""Data access: NASA Earthdata (earthaccess) with NASA POWER fallback, plus caching.

Everything returns an xarray.DataArray with dims (time, lat, lon) in RAW file units.
Unit conversion happens later in processing.py, so caches stay faithful to NASA files.

Credentials: the Earthdata token is read ONLY from the environment variable
EARTHDATA_TOKEN. It is never written to any file.

Original code written for NASA Space Apps 2026.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import pandas as pd
import requests
import xarray as xr

from .config import BBox, DEMOS, Variable

ProgressFn = Optional[Callable[[float, str], None]]

DEMO_DIR = Path(__file__).resolve().parent.parent / "data" / "demo_cache"
POWER_URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"


AUTHORIZE_HELP = (
    "NASA refused the download (403 Forbidden). Your login works, but you must approve the data server once: "
    "log in at urs.earthdata.nasa.gov > Applications > Authorized Apps > Approve More Applications, "
    "then approve 'NASA GESDISC DATA ARCHIVE' (also 'GES DISC' if listed) and accept the license. Then run again.")


class DataUnavailable(RuntimeError):
    """Raised when data cannot be fetched; the message is safe to show to students."""


# ----------------------------------------------------------------------------- cache
def cache_dir() -> Path:
    d = Path(os.environ.get("TD_CACHE_DIR", ".td_cache"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def cache_path(var: Variable, bbox: BBox, y0: int, y1: int, source: str) -> Path:
    raw = f"{var.key}|{var.short_name}|{var.version}|{[round(b, 3) for b in bbox]}|{y0}|{y1}|{source}"
    return cache_dir() / f"{var.key}_{hashlib.sha1(raw.encode()).hexdigest()[:12]}.nc"


# ----------------------------------------------------------------------------- helpers
def _norm_dims(da: xr.DataArray) -> xr.DataArray:
    """Rename lat/lon-like dims, sort ascending, order as (time, lat, lon)."""
    rename = {}
    for d in da.dims:
        low = d.lower()
        if low in ("latitude", "ydim") and d != "lat":
            rename[d] = "lat"
        if low in ("longitude", "xdim") and d != "lon":
            rename[d] = "lon"
    da = da.rename(rename)
    if "lat" not in da.dims or "lon" not in da.dims:
        raise DataUnavailable(f"Unexpected dimensions {da.dims}: expected lat/lon.")
    da = da.sortby("lat").sortby("lon")
    extra = [d for d in da.dims if d not in ("lat", "lon")]
    return da.transpose(*extra, "lat", "lon")


def _subset_box(da: xr.DataArray, bbox: BBox, pad: float = 0.0) -> xr.DataArray:
    w, s, e, n = bbox
    return da.sel(lat=slice(s - pad, n + pad), lon=slice(w - pad, e + pad))


def _pick_var(ds: xr.Dataset, candidates: tuple[str, ...]) -> xr.DataArray:
    for name in candidates:
        if name in ds.data_vars:
            return ds[name]
    raise DataUnavailable(
        f"None of {candidates} found in file. Variables present: {list(ds.data_vars)[:15]}. "
        "Fix `var_names` in src/config.py."
    )


def _granule_month(granule) -> pd.Timestamp:
    """Month start taken from CMR metadata (more reliable than decoding file time axes)."""
    begin = granule["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"]
    ts = pd.Timestamp(begin)
    if ts.tzinfo is not None:
        ts = ts.tz_convert(None)
    return pd.Timestamp(year=ts.year, month=ts.month, day=1)


# ----------------------------------------------------------------------------- earthaccess
def earthaccess_login():
    import earthaccess  # imported lazily so unit tests and demo mode do not need it

    if not os.environ.get("EARTHDATA_TOKEN"):
        raise DataUnavailable("EARTHDATA_TOKEN is not set. Create one at urs.earthdata.nasa.gov > Generate Token.")
    auth = earthaccess.login(strategy="environment")
    if not getattr(auth, "authenticated", True):
        raise DataUnavailable("Earthdata login failed. The token may be expired or revoked: generate a new one.")
    return earthaccess


def fetch_earthaccess(var: Variable, bbox: BBox, y0: int, y1: int, progress: ProgressFn = None) -> xr.DataArray:
    """Stream monthly files one by one, keep only the bounding box, and stack them in time."""
    if var.status != "ready":
        raise DataUnavailable(f"'{var.label}' is a planned stretch goal and is not implemented yet.")
    ea = earthaccess_login()

    # A 1-degree pad lets tiny boxes still catch at least one grid cell.
    results = ea.search_data(
        short_name=var.short_name, version=var.version,
        temporal=(f"{y0}-01-01", f"{y1}-12-31"), count=3000,
    )
    if not results:
        raise DataUnavailable(f"No files found for {var.short_name} v{var.version}, {y0}-{y1}.")

    files = ea.open(results)  # file-like objects streamed over HTTPS, nothing saved except our subset
    pieces = []
    for i, (g, f) in enumerate(zip(results, files)):
        month = _granule_month(g)
        if not (y0 <= month.year <= y1):
            continue
        try:
            ds = xr.open_dataset(f, engine="h5netcdf", group=var.group, decode_times=False)
        except Exception as exc:  # noqa: BLE001
            if any(code in str(exc) for code in ("403", "401", "Forbidden", "Unauthorized")):
                raise DataUnavailable(AUTHORIZE_HELP) from exc
            ds = xr.open_dataset(f, engine="h5netcdf", decode_times=False)  # root-group fallback
        da = _norm_dims(_pick_var(ds, var.var_names))
        for d in [d for d in da.dims if d not in ("lat", "lon")]:
            da = da.isel({d: 0}, drop=True)
        sub = _subset_box(da, bbox, pad=1.0).load()
        sub = sub.expand_dims(time=[month])
        pieces.append(sub)
        ds.close()
        if progress:
            progress((i + 1) / len(results), f"Downloaded {month:%Y-%m}")
    if not pieces:
        raise DataUnavailable("Files were found but none matched the requested years.")
    out = xr.concat(pieces, dim="time").sortby("time")
    out.name = var.key
    out.attrs.update(source=f"NASA {var.short_name} v{var.version} via earthaccess", raw_variable=var.var_names[0])
    return out


# ----------------------------------------------------------------------------- POWER fallback
def parse_power_json(payload: dict, param: str) -> pd.Series:
    """Turn a POWER monthly JSON response into a monthly pandas Series.

    Format (from POWER docs, VERIFY on first live call):
      payload["properties"]["parameter"][param] = {"200001": 12.3, ..., "200013": annual mean}
    Month 13 is the annual value and is dropped. -999 means missing.
    """
    try:
        raw = payload["properties"]["parameter"][param]
    except KeyError as exc:
        raise DataUnavailable(f"Unexpected POWER response; missing {exc}.") from exc
    rows = {}
    for key, val in raw.items():
        year, month = int(key[:4]), int(key[4:])
        if month == 13:
            continue
        rows[pd.Timestamp(year=year, month=month, day=1)] = np.nan if val in (-999, -999.0) else float(val)
    return pd.Series(rows).sort_index()


def fetch_power(var: Variable, bbox: BBox, y0: int, y1: int) -> xr.DataArray:
    """NASA POWER gives one point, so we query the CENTRE of the box (a coarser answer)."""
    if not var.power_param:
        raise DataUnavailable(f"NASA POWER has no fallback for '{var.label}'.")
    w, s, e, n = bbox
    params = dict(parameters=var.power_param, community="AG", longitude=round((w + e) / 2, 3),
                  latitude=round((s + n) / 2, 3), start=y0, end=y1, format="JSON")
    try:
        r = requests.get(POWER_URL, params=params, timeout=60)
        r.raise_for_status()
        series = parse_power_json(r.json(), var.power_param)
    except requests.RequestException as exc:
        raise DataUnavailable(f"NASA POWER request failed: {exc}") from exc
    lat, lon = params["latitude"], params["longitude"]
    da = xr.DataArray(series.values.reshape(-1, 1, 1), coords={"time": series.index, "lat": [lat], "lon": [lon]},
                      dims=("time", "lat", "lon"), name=var.key)
    # POWER's T2M is already in °C and PRECTOTCORR already in mm/day -> mark so processing skips conversion.
    da.attrs.update(source="NASA POWER (point at box centre)", already_converted=True)
    return da


# ----------------------------------------------------------------------------- public API
def get_cube(var: Variable, bbox: BBox, y0: int, y1: int, progress: ProgressFn = None) -> xr.DataArray:
    """Cache -> earthaccess -> POWER. The data source is recorded in the cube's attrs['source']."""
    for source in ("earthaccess", "power"):
        path = cache_path(var, bbox, y0, y1, source)
        if path.exists():
            with xr.open_dataarray(path) as cached:
                out = cached.load()
            out.attrs["source"] = out.attrs.get("source", source) + " (cached)"
            return out
    errors = []
    try:
        cube = fetch_earthaccess(var, bbox, y0, y1, progress)
        cube.to_netcdf(cache_path(var, bbox, y0, y1, "earthaccess"))
        return cube
    except Exception as exc:  # noqa: BLE001 - we want to fall back on any failure
        errors.append(f"earthaccess: {exc}")
    try:
        cube = fetch_power(var, bbox, y0, y1)
        cube.attrs["fallback_reason"] = errors[0]
        cube.to_netcdf(cache_path(var, bbox, y0, y1, "power"))
        return cube
    except Exception as exc:  # noqa: BLE001
        errors.append(f"power: {exc}")
    raise DataUnavailable(" | ".join(errors))


def demo_path(demo_id: str) -> Path:
    return DEMO_DIR / f"{demo_id}.nc"


def demo_available(demo_id: str) -> bool:
    return demo_path(demo_id).exists()


def load_demo(demo_id: str) -> xr.DataArray:
    if demo_id not in DEMOS:
        raise DataUnavailable(f"Unknown demo '{demo_id}'.")
    if not demo_available(demo_id):
        raise DataUnavailable(
            "Demo cache not built yet. Run `python scripts/build_demo_cache.py` once with your "
            "EARTHDATA_TOKEN set, then commit data/demo_cache/*.nc.")
    with xr.open_dataarray(demo_path(demo_id)) as da:
        out = da.load()
    out.attrs["source"] = out.attrs.get("source", "demo cache") + " (demo cache)"
    return out
