# Test checklist

## Automated (run `python -m pytest -q`; synthetic data with a known answer, no network)
- [x] Recovers a known +0.30/decade trend (Theil-Sen and OLS), CI contains truth
- [x] No-trend series is "visible but not yet significant"
- [x] Falling trend wording; seasonal cycle removed (each month's anomaly mean is 0)
- [x] Latitude weighting is cos(lat); missing cells ignored; tiny box uses nearest cell; bad box rejected
- [x] Fewer than 60 months is refused with a clear message
- [x] POWER JSON parser: drops annual month 13 and -999
- [x] Plots build; verdict card HTML-escapes text; pixel map signs/significance
- [x] Catalog has 8-10 variables each with definition; app runs headless in dev-synthetic mode

## Manual, needs YOUR token and internet (NOT yet verified by the assistant)
- [ ] `earthaccess` login works with EARTHDATA_TOKEN
- [ ] MERRA-2 T2M fetch for a small box, 5 years: values look like plausible °C
- [ ] TQV exists in the monthly MERRA-2 file; GPM group is `Grid`; GPM lat/lon order handled
- [ ] Compare one MERRA-2 T2M result against NASA Giovanni for the same box (sanity check)
- [ ] POWER fallback: unset token, run T2M; confirm JSON shape matches `parse_power_json`
- [ ] `build_demo_cache.py` makes 3 small .nc files; demos then work offline
- [ ] Space boots on Hugging Face; secret is read; no token appears in the repo or logs
