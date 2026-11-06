"""Tests for data cleaning, summary tables, figures and the regeneration script."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agri_analysis import analysis as A  # noqa: E402
from agri_analysis import plots  # noqa: E402
from agri_analysis.data import SEASON_ORDER, clean_data, load_data, validate_data  # noqa: E402


@pytest.fixture(scope="module")
def raw() -> pd.DataFrame:
    return load_data()


@pytest.fixture(scope="module")
def df(raw) -> pd.DataFrame:
    return clean_data(raw)


def test_raw_shape_and_keys(raw):
    assert raw.shape == (4000, 28)
    assert raw["Farm_ID"].is_unique


def test_accounting_identities_hold(raw):
    v = validate_data(raw).set_index("Check")["Max_Abs_Deviation"]
    # Deviations are only CSV rounding (2-3 decimal places, whole rupees).
    assert v["Production = Yield x Area"] <= 0.01
    assert v["Revenue = Production x Price"] <= 1
    assert v["Profit = Revenue - Cost"] == 0
    assert v["Water efficiency = Production / Water x 1000"] <= 0.001


def test_cleaning_recovers_every_yield(raw, df):
    assert df["Yield_Tonnes_Ha"].notna().all()
    assert df["Yield_Imputed"].sum() == raw["Yield_Tonnes_Ha"].isna().sum()
    # Original values are untouched.
    keep = raw["Yield_Tonnes_Ha"].notna()
    assert np.allclose(df.loc[keep, "Yield_Tonnes_Ha"], raw.loc[keep, "Yield_Tonnes_Ha"])
    # Rainfall / soil moisture gaps are NOT invented.
    assert df["Rainfall_mm"].isna().sum() == raw["Rainfall_mm"].isna().sum()


def test_clean_data_does_not_mutate_input(raw):
    before = raw.copy()
    clean_data(raw)
    pd.testing.assert_frame_equal(raw, before)


def test_spearman_matches_rank_definition():
    a = pd.Series([1, 2, 3, 4, 5, np.nan])
    assert A.spearman(a, a ** 3) == pytest.approx(1.0)
    assert A.spearman(a, -a) == pytest.approx(-1.0)


def test_yield_index_is_centred_per_crop(df):
    med = df.groupby("Crop")["Yield_Index"].median()
    assert np.allclose(med, 1.0)


def test_season_summary_matches_original_results(df):
    ss = A.season_summary(df)
    assert list(ss.index) == SEASON_ORDER
    assert ss["Farms"].sum() == 4000
    # Unchanged from the first version of the project (these use no imputed data).
    assert ss.loc["Kharif", "Total_Production_Tonnes"] == pytest.approx(82387.61)
    assert ss.loc["Zaid", "Avg_Profit_INR"] == pytest.approx(-24804.82, abs=0.01)


def test_season_ordering_holds_for_every_crop(df):
    sc = A.seasonal_yield_change(df)
    assert (sc["Rabi_vs_Kharif_pct"] < 0).all()
    assert (sc["Zaid_vs_Kharif_pct"] < sc["Rabi_vs_Kharif_pct"]).all()


def test_crop_and_irrigation_summaries(df):
    cs = A.crop_summary(df)
    assert set(cs.index[:2]) == {"Sugarcane", "Chilli"}
    irr = A.irrigation_summary(df)
    assert irr["Median_Yield_Index"].idxmax() == "Drip"
    assert irr["Median_Water_Index"].idxmax() == "Flood"


def test_yield_drivers_exclude_derived_columns(df):
    d = A.yield_drivers(df)
    for derived in ["Production_Tonnes", "Revenue_INR", "Profit_INR", "Water_Efficiency_t_per_1000m3"]:
        assert derived not in d.index
    assert d["Spearman_vs_Yield_Index"].abs().max() < 0.5


def test_pest_effect_is_confounded(df):
    pooled = A.spearman(df["Disease_Pest_Risk_pct"], df["Yield_Index"])
    assert pooled > 0.1
    assert abs(A.pest_partial_correlation(df)) < 0.1


def test_key_findings_are_generated(df):
    findings = A.key_findings(df)
    assert len(findings) >= 6
    assert all(isinstance(f, str) and f for f in findings)


def test_summaries_work_on_a_filtered_subset(df):
    sub = df[df["State"] == "Punjab"]
    assert A.season_summary(sub)["Farms"].sum() == len(sub)
    assert not A.crop_summary(sub).empty


@pytest.mark.parametrize("name", list(plots.FIGURES))
def test_every_figure_renders(df, name):
    fig = plots.FIGURES[name](df)
    assert fig.axes
    plt.close(fig)


def test_run_analysis_script(tmp_path):
    sys.path.insert(0, str(ROOT / "scripts"))
    import run_analysis

    assert run_analysis.main(["--out", str(tmp_path)]) == 0
    assert len(list((tmp_path / "figures").glob("*.png"))) == len(plots.FIGURES)
    assert (tmp_path / "tables" / "season_summary.csv").exists()
    assert "Key findings" in (tmp_path / "key_findings.md").read_text(encoding="utf-8")
