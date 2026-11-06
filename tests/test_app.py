"""Smoke tests for the Streamlit dashboard using Streamlit's built-in test harness."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture(autouse=True)
def _run_from_project_root(monkeypatch):
    monkeypatch.chdir(Path(APP).parent)


def test_app_runs_with_default_filters():
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    assert at.metric[0].value == "4,000"
    assert len(at.tabs) == 5


def test_app_handles_a_narrow_filter():
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.multiselect[1].set_value(["Rabi"]).run()  # season filter
    assert not at.exception
    assert any("Select all three seasons" in i.value for i in at.info)


def test_app_handles_empty_selection():
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.multiselect[2].set_value([]).run()  # crop filter
    assert not at.exception
    assert any("No records match" in w.value for w in at.warning)
