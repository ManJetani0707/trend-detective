"""Linear trend statistics on monthly anomalies.

Primary test: Mann-Kendall (pymannkendall) + Theil-Sen slope (scipy).
Cross-check: ordinary least squares slope with a 95% confidence interval.
Extra honesty check: Hamed-Rao Mann-Kendall, which corrects for autocorrelation.

Only LINEAR trends are tested. Non-linear trends are future work.

Original code written for NASA Space Apps 2026.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import pymannkendall as mk
from scipy import stats as sps
import xarray as xr

from .config import ALPHA, MIN_MONTHS


def decimal_years(index: pd.DatetimeIndex) -> np.ndarray:
    idx = pd.DatetimeIndex(index)
    return idx.year.to_numpy() + (idx.month.to_numpy() - 0.5) / 12.0


@dataclass
class TrendResult:
    n: int
    start: pd.Timestamp
    end: pd.Timestamp
    sen_per_decade: float
    sen_lo_per_decade: float
    sen_hi_per_decade: float
    sen_intercept: float          # intercept for y = intercept + slope_per_year * decimal_year
    mk_trend: str                 # "increasing" | "decreasing" | "no trend"
    mk_p: float
    mk_tau: float
    hr_p: float                   # Hamed-Rao (autocorrelation-aware) p-value
    ols_per_decade: float
    ols_lo_per_decade: float
    ols_hi_per_decade: float
    ols_intercept: float
    ols_resid_sd: float
    alpha: float = ALPHA

    @property
    def significant(self) -> bool:
        return self.mk_p < self.alpha


def analyze_trend(anom: pd.Series, alpha: float = ALPHA) -> TrendResult:
    y = anom.dropna()
    if len(y) < MIN_MONTHS:
        raise ValueError(f"Need at least {MIN_MONTHS} months; got {len(y)}.")
    x = decimal_years(y.index)
    yv = y.to_numpy(dtype=float)

    ts_slope, ts_int, ts_lo, ts_hi = sps.theilslopes(yv, x, alpha=1 - alpha)
    mk_res = mk.original_test(yv, alpha=alpha)
    hr_res = mk.hamed_rao_modification_test(yv, alpha=alpha)

    lr = sps.linregress(x, yv)
    tcrit = sps.t.ppf(1 - alpha / 2, len(yv) - 2)
    resid = yv - (lr.intercept + lr.slope * x)

    return TrendResult(
        n=len(yv), start=y.index[0], end=y.index[-1],
        sen_per_decade=ts_slope * 10, sen_lo_per_decade=ts_lo * 10, sen_hi_per_decade=ts_hi * 10,
        sen_intercept=float(ts_int),
        mk_trend=str(mk_res.trend), mk_p=float(mk_res.p), mk_tau=float(mk_res.Tau), hr_p=float(hr_res.p),
        ols_per_decade=lr.slope * 10,
        ols_lo_per_decade=(lr.slope - tcrit * lr.stderr) * 10,
        ols_hi_per_decade=(lr.slope + tcrit * lr.stderr) * 10,
        ols_intercept=float(lr.intercept), ols_resid_sd=float(np.sqrt(np.sum(resid**2) / (len(yv) - 2))),
        alpha=alpha,
    )


def ols_band(anom: pd.Series, res: TrendResult, alpha: float = ALPHA):
    """OLS fitted line and its (1-alpha) confidence band for the MEAN line."""
    y = anom.dropna()
    x = decimal_years(y.index)
    n = len(x)
    slope = res.ols_per_decade / 10
    fit = res.ols_intercept + slope * x
    sxx = np.sum((x - x.mean()) ** 2)
    se = res.ols_resid_sd * np.sqrt(1.0 / n + (x - x.mean()) ** 2 / sxx)
    t = sps.t.ppf(1 - alpha / 2, n - 2)
    return y.index, fit, fit - t * se, fit + t * se


def sen_line(anom: pd.Series, res: TrendResult):
    y = anom.dropna()
    x = decimal_years(y.index)
    return y.index, res.sen_intercept + (res.sen_per_decade / 10) * x


def verdict(res: TrendResult, units: str, label: str) -> dict:
    """Plain-language verdict following the project rule: p < 0.05 -> significant."""
    rising = res.sen_per_decade > 0
    direction = "rising" if rising else "falling"
    total = res.sen_per_decade * (res.end.year - res.start.year + 1) / 10
    caution = []
    if res.significant and res.hr_p >= res.alpha:
        caution.append("The autocorrelation-aware check (Hamed-Rao) is NOT significant, so treat this result with extra care.")
    if not res.significant and res.hr_p < res.alpha:
        caution.append("The autocorrelation-aware check (Hamed-Rao) IS significant, so a trend may be present.")
    ols_agree = (res.ols_lo_per_decade > 0) or (res.ols_hi_per_decade < 0)
    if res.significant != ols_agree:
        caution.append("Mann-Kendall and the OLS confidence interval disagree on significance; the signal is borderline.")

    if res.significant:
        return dict(kind="significant", color="#c0392b" if rising else "#2471a3",
                    headline=f"Significant {direction} trend",
                    detail=f"{label} changed by about {res.sen_per_decade:+.3g} {units} per decade "
                           f"(about {total:+.3g} {units} over the whole period).",
                    caution=caution)
    return dict(kind="not_significant", color="#7f8c8d",
                headline="Visible but not yet significant",
                detail=f"{label} shows a slight {direction} tendency ({res.sen_per_decade:+.3g} {units} per decade), "
                       "but it could be chance. A longer record may help.",
                caution=caution)


def pixel_trends(anom_cube: xr.DataArray, alpha: float = ALPHA, max_pixels: int = 1500):
    """Theil-Sen slope (per decade) and Mann-Kendall p-value for every grid cell.

    Returns (slope, pvalue, stride). If the box has too many cells we sub-sample with a
    stride so the loop stays quick; the stride is reported so the app can tell the user.
    """
    nlat, nlon = anom_cube.sizes["lat"], anom_cube.sizes["lon"]
    stride = 1
    while (np.ceil(nlat / stride) * np.ceil(nlon / stride)) > max_pixels:
        stride += 1
    cube = anom_cube.isel(lat=slice(None, None, stride), lon=slice(None, None, stride))
    x = decimal_years(pd.DatetimeIndex(cube["time"].values))
    slope = np.full((cube.sizes["lat"], cube.sizes["lon"]), np.nan)
    pval = np.full_like(slope, np.nan)
    data = cube.transpose("time", "lat", "lon").values
    for i in range(slope.shape[0]):
        for j in range(slope.shape[1]):
            col = data[:, i, j]
            ok = np.isfinite(col)
            if ok.sum() < MIN_MONTHS:
                continue
            slope[i, j] = sps.theilslopes(col[ok], x[ok])[0] * 10
            pval[i, j] = mk.original_test(col[ok], alpha=alpha).p
    out_slope = xr.DataArray(slope, coords={"lat": cube["lat"], "lon": cube["lon"]}, dims=("lat", "lon"))
    out_p = xr.DataArray(pval, coords=out_slope.coords, dims=("lat", "lon"))
    return out_slope, out_p, stride
