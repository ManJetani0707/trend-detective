"""Plotly figures and the verdict card.

Original code written for NASA Space Apps 2026.
"""
from __future__ import annotations

import html

import numpy as np
import plotly.graph_objects as go
import pandas as pd
import xarray as xr

from .stats import TrendResult, ols_band, sen_line


def timeseries_figure(anom: pd.Series, res: TrendResult, units: str, title: str) -> go.Figure:
    idx, fit, lo, hi = ols_band(anom, res)
    sidx, sline = sen_line(anom, res)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=idx, y=hi, mode="lines", line=dict(width=0), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=idx, y=lo, mode="lines", line=dict(width=0), fill="tonexty",
                             fillcolor="rgba(52,73,94,0.18)", name="95% CI of OLS trend line", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=anom.index, y=anom.values, mode="lines", name="Monthly anomaly",
                             line=dict(color="#7f8c8d", width=1.2)))
    fig.add_trace(go.Scatter(x=sidx, y=sline, mode="lines", name=f"Theil-Sen trend ({res.sen_per_decade:+.3g} {units}/decade)",
                             line=dict(color="#c0392b", width=3)))
    fig.add_hline(y=0, line=dict(color="#bbb", width=1, dash="dot"))
    fig.update_layout(title=title, xaxis_title="Year", yaxis_title=f"Anomaly ({units})",
                      legend=dict(orientation="h", y=-0.2), margin=dict(l=40, r=20, t=60, b=40),
                      template="plotly_white", hovermode="x unified")
    return fig


def seasonal_figure(clim: pd.Series, units: str) -> go.Figure:
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    fig = go.Figure(go.Bar(x=[months[m - 1] for m in clim.index], y=clim.values, marker_color="#5d6d7e"))
    fig.update_layout(title="Typical seasonal cycle (removed before testing the trend)", yaxis_title=units,
                      template="plotly_white", margin=dict(l=40, r=20, t=60, b=40))
    return fig


def fmt_p(p: float) -> str:
    """A p-value is never exactly 0, so tiny values are shown as '< 0.001'."""
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


def verdict_card_html(v: dict, res: TrendResult, units: str, region: str, source: str) -> str:
    e = html.escape
    cautions = "".join(f"<li>{e(c)}</li>" for c in v["caution"])
    caution_block = f"<ul style='margin:8px 0 0 18px;color:#7d6608'>{cautions}</ul>" if cautions else ""
    return f"""
<div style="border-left:8px solid {v['color']};background:#f8f9f9;padding:16px 20px;border-radius:8px;color:#1b2631">
  <div style="font-size:1.5rem;font-weight:700;color:{v['color']}">{e(v['headline'])}</div>
  <div style="font-size:1.05rem;margin:6px 0 10px 0">{e(v['detail'])}</div>
  <table style="font-size:0.95rem;border-collapse:collapse">
    <tr><td style="padding-right:14px"><b>Where</b></td><td>{e(region)}</td></tr>
    <tr><td><b>Period</b></td><td>{res.start:%b %Y} to {res.end:%b %Y} ({res.n} months)</td></tr>
    <tr><td><b>Theil-Sen slope</b></td><td>{res.sen_per_decade:+.3g} {e(units)}/decade (95% CI {res.sen_lo_per_decade:+.3g} to {res.sen_hi_per_decade:+.3g})</td></tr>
    <tr><td><b>Mann-Kendall p</b></td><td>{fmt_p(res.mk_p)} (threshold {res.alpha})</td></tr>
    <tr><td><b>OLS cross-check</b></td><td>{res.ols_per_decade:+.3g} {e(units)}/decade (95% CI {res.ols_lo_per_decade:+.3g} to {res.ols_hi_per_decade:+.3g})</td></tr>
    <tr><td><b>Data source</b></td><td>{e(source)}</td></tr>
  </table>
  {caution_block}
</div>"""


def trend_map_figure(slope: xr.DataArray, pval: xr.DataArray, units: str, alpha: float = 0.05) -> go.Figure:
    """Red = rising, blue = falling. Cells that are NOT significant are marked with an 'x' (hatching)."""
    lat, lon = slope["lat"].values, slope["lon"].values
    z = slope.values
    lim = float(np.nanmax(np.abs(z))) if np.isfinite(z).any() else 1.0
    fig = go.Figure(go.Heatmap(z=z, x=lon, y=lat, zmin=-lim, zmax=lim, colorscale="RdBu_r",
                               colorbar=dict(title=f"{units}/decade"), hoverongaps=False))
    ns = np.isfinite(pval.values) & (pval.values >= alpha)
    ii, jj = np.where(ns)
    if len(ii):
        fig.add_trace(go.Scatter(x=lon[jj], y=lat[ii], mode="markers", name="Not significant (p ≥ 0.05)",
                                 marker=dict(symbol="x-thin", size=7, color="rgba(0,0,0,0.55)", line=dict(width=1))))
    fig.update_layout(title="Where is it changing? Trend per grid cell (x = not significant)",
                      xaxis_title="Longitude", yaxis_title="Latitude", template="plotly_white",
                      margin=dict(l=40, r=20, t=60, b=40), legend=dict(orientation="h", y=-0.2))
    padx = max((lon.max() - lon.min()) * 0.03, 0.1)
    pady = max((lat.max() - lat.min()) * 0.03, 0.1)
    fig.update_xaxes(range=[lon.min() - padx, lon.max() + padx], constrain="domain")
    fig.update_yaxes(range=[lat.min() - pady, lat.max() + pady], scaleanchor="x", scaleratio=1, constrain="domain")
    fig.update_layout(height=560)
    return fig
