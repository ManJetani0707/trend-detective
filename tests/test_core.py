"""Tests use SYNTHETIC data with a KNOWN answer. No NASA data, no network."""
import numpy as np
import pandas as pd
import pytest
import xarray as xr

from src.config import VARIABLES
from src.data import parse_power_json, DataUnavailable
from src.plots import timeseries_figure, trend_map_figure, verdict_card_html
from src.processing import RecordTooShort, area_average, build_series, clip_region, monthly_anomalies, pixel_anomaly_cube
from src.stats import analyze_trend, pixel_trends, verdict
from src.synthetic import synthetic_cube

VAR = VARIABLES["merra2_t2m"]
BOX = (69.0, 21.0, 73.0, 24.0)


def _series(trend, seed=1, noise=0.4):
    cube = synthetic_cube(trend_per_decade=trend, seed=seed, noise=noise)
    return build_series(cube, BOX, VAR)


def test_recovers_known_trend():
    res = analyze_trend(_series(0.30)["anomalies"])
    assert res.sen_per_decade == pytest.approx(0.30, abs=0.06)
    assert res.ols_per_decade == pytest.approx(0.30, abs=0.06)
    assert res.ols_lo_per_decade < 0.30 < res.ols_hi_per_decade
    assert res.significant and res.mk_trend == "increasing"


def test_no_trend_is_not_significant():
    res = analyze_trend(_series(0.0, seed=3)["anomalies"])
    assert not res.significant
    assert verdict(res, "°C", "x")["kind"] == "not_significant"


def test_falling_trend_wording():
    res = analyze_trend(_series(-0.4)["anomalies"])
    v = verdict(res, "°C", "Air temperature")
    assert v["headline"] == "Significant falling trend"


def test_anomalies_remove_seasonal_cycle():
    anom = _series(0.0)["anomalies"]
    by_month = anom.groupby(anom.index.month).mean()
    assert by_month.abs().max() < 1e-9


def test_record_too_short():
    cube = synthetic_cube(years=(2001, 2003))
    with pytest.raises(RecordTooShort):
        build_series(cube, BOX, VAR)


def test_latitude_weighting():
    lat = np.array([0.0, 60.0])
    da = xr.DataArray(np.array([[[10.0], [20.0]]]), coords={"time": [pd.Timestamp("2001-01-01")], "lat": lat, "lon": [0.0]},
                      dims=("time", "lat", "lon"))
    got = float(area_average(da).iloc[0])
    expected = (10 * 1.0 + 20 * 0.5) / 1.5   # cos(0)=1, cos(60)=0.5
    assert got == pytest.approx(expected)
    assert got != pytest.approx(15.0)


def test_missing_values_ignored():
    cube = synthetic_cube(trend_per_decade=0.2)
    cube[:, 0, :] = np.nan                    # a whole row of missing cells
    res = analyze_trend(build_series(cube, BOX, VAR)["anomalies"])
    assert res.sen_per_decade == pytest.approx(0.2, abs=0.06)


def test_tiny_box_uses_nearest_cell():
    cube = synthetic_cube()
    clipped = clip_region(cube, (70.01, 22.01, 70.02, 22.02))
    assert clipped.sizes["lat"] == 1 and clipped.sizes["lon"] == 1
    assert "nearest" in clipped.attrs["clip_note"]


def test_bad_box_rejected():
    with pytest.raises(ValueError):
        clip_region(synthetic_cube(), (74.0, 20.0, 70.0, 24.0))


def test_power_parser_drops_annual_and_missing():
    payload = {"properties": {"parameter": {"T2M": {"200001": 20.5, "200002": -999, "200013": 21.0, "200101": 19.0}}}}
    s = parse_power_json(payload, "T2M")
    assert list(s.index) == [pd.Timestamp("2000-01-01"), pd.Timestamp("2000-02-01"), pd.Timestamp("2001-01-01")]
    assert np.isnan(s.iloc[1]) and s.iloc[0] == 20.5


def test_power_parser_bad_payload():
    with pytest.raises(DataUnavailable):
        parse_power_json({"oops": 1}, "T2M")


def test_figures_build():
    out = _series(0.3)
    res = analyze_trend(out["anomalies"])
    fig = timeseries_figure(out["anomalies"], res, "°C", "t")
    assert len(fig.data) == 4
    html = verdict_card_html(verdict(res, "°C", "<b>x</b>"), res, "°C", "Region <script>", "src")
    assert "<script>" not in html and "&lt;script&gt;" in html


def test_pixel_map_signs_and_significance():
    cube = synthetic_cube(trend_per_decade=0.5, step=1.0, bbox=(69, 21, 72, 24))
    out = build_series(cube, (69, 21, 72, 24), VAR)
    slope, pval, stride = pixel_trends(pixel_anomaly_cube(out["clipped"]))
    assert stride == 1 and slope.shape == (4, 4)
    assert float(slope.mean()) == pytest.approx(0.5, abs=0.1)
    assert float(pval.max()) < 0.05
    fig = trend_map_figure(slope, pval, "°C")
    assert fig.data[0].type == "heatmap"


def test_catalog_has_8_to_10_variables_and_definitions():
    assert 8 <= len(VARIABLES) <= 10
    assert all(v.definition and v.units for v in VARIABLES.values())
    assert sum(v.status == "ready" for v in VARIABLES.values()) >= 6


def test_p_value_formatting():
    from src.plots import fmt_p
    assert fmt_p(0.0) == "< 0.001"
    assert fmt_p(0.0234) == "0.023"


def test_authorize_help_mentions_the_app_name():
    from src.data import AUTHORIZE_HELP
    assert "NASA GESDISC DATA ARCHIVE" in AUTHORIZE_HELP
