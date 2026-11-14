"""Headless UI smoke test using Streamlit's AppTest and SYNTHETIC data (dev switch)."""
from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_app_runs_guided_flow_with_synthetic_data(monkeypatch):
    monkeypatch.setenv("TD_DEV_SYNTHETIC", "1")
    at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"), default_timeout=120).run()
    assert not at.exception
    assert any("DEV MODE" in e.value for e in at.error)          # warning banner is shown
    at.button[0].click().run()                                   # Investigate
    assert not at.exception
    assert any("trend" in m.value.lower() or "significant" in m.value.lower() for m in at.markdown)
