"""Loading, validation and cleaning of the agriculture dataset."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "agriculture_data.csv"

SEASON_ORDER = ["Kharif", "Rabi", "Zaid"]
IRRIGATION_ORDER = ["Drip", "Sprinkler", "Flood", "Rainfed"]

CATEGORICAL_COLUMNS = ["Farm_ID", "State", "District", "Crop", "Season", "Irrigation_Method"]

EXPECTED_COLUMNS = [
    "Farm_ID", "State", "District", "Crop", "Season", "Farm_Area_Hectares",
    "Rainfall_mm", "Avg_Temperature_C", "Humidity_pct", "Sunlight_Hours_Day",
    "Soil_pH", "Soil_Moisture_pct", "Nitrogen_kg_ha", "Phosphorus_kg_ha",
    "Potassium_kg_ha", "Irrigation_Method", "Fertilizer_kg_ha", "Pesticide_Litre_ha",
    "Seed_Quality_Score", "Yield_Tonnes_Ha", "Production_Tonnes",
    "Market_Price_INR_Tonne", "Total_Cost_INR", "Revenue_INR", "Profit_INR",
    "Water_Used_m3", "Water_Efficiency_t_per_1000m3", "Disease_Pest_Risk_pct",
]


def load_data(path: str | Path = DATA_PATH) -> pd.DataFrame:
    """Read the raw CSV exactly as supplied."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found at {path}. Run commands from the project root "
            "or pass the path to the CSV explicitly."
        )
    df = pd.read_csv(path)
    missing = set(EXPECTED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Dataset is missing expected columns: {sorted(missing)}")
    return df


def validate_data(df: pd.DataFrame) -> pd.DataFrame:
    """Check the accounting identities the dataset is built on.

    Returns a small table with the largest absolute deviation for each
    identity, so the notebook and tests can show that derived columns agree
    with their inputs (up to the rounding used in the CSV).
    """
    checks = {
        "Production = Yield x Area": (
            df["Production_Tonnes"] - df["Yield_Tonnes_Ha"] * df["Farm_Area_Hectares"]
        ),
        "Revenue = Production x Price": (
            df["Revenue_INR"] - df["Production_Tonnes"] * df["Market_Price_INR_Tonne"]
        ),
        "Profit = Revenue - Cost": df["Profit_INR"] - (df["Revenue_INR"] - df["Total_Cost_INR"]),
        "Water efficiency = Production / Water x 1000": (
            df["Water_Efficiency_t_per_1000m3"]
            - df["Production_Tonnes"] / df["Water_Used_m3"] * 1000
        ),
    }
    rows = [
        {"Check": name, "Rows_Checked": int(diff.notna().sum()), "Max_Abs_Deviation": float(diff.abs().max())}
        for name, diff in checks.items()
    ]
    return pd.DataFrame(rows)


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Return an analysis-ready copy of the raw data.

    * Missing ``Yield_Tonnes_Ha`` values are recovered exactly from
      ``Production_Tonnes / Farm_Area_Hectares`` (the identity holds for every
      complete row). The flag ``Yield_Imputed`` records which rows were filled.
    * Missing ``Rainfall_mm`` / ``Soil_Moisture_pct`` are left as NaN; statistics
      that use them drop those rows pairwise instead of inventing values.
    * Categorical columns get a stable, agronomically meaningful order.
    * Derived, crop-comparable metrics are added (see below).

    Derived columns
    ---------------
    Yield_Index        yield / median yield of the same crop (1.0 = typical for that crop)
    Profit_per_Ha      profit per hectare (INR) - removes the farm-size effect
    Profit_Margin      profit / total cost
    Water_m3_per_Ha    irrigation + rain-fed water use per hectare
    Water_Index        Water_m3_per_Ha / median for the same crop
    Is_Profitable      profit > 0
    """
    out = df.copy()
    for col in ["State", "District", "Crop", "Season", "Irrigation_Method"]:
        out[col] = out[col].astype(str).str.strip()

    out["Yield_Imputed"] = out["Yield_Tonnes_Ha"].isna()
    out.loc[out["Yield_Imputed"], "Yield_Tonnes_Ha"] = (
        out["Production_Tonnes"] / out["Farm_Area_Hectares"]
    ).round(2)

    out["Season"] = pd.Categorical(out["Season"], categories=SEASON_ORDER, ordered=True)
    out["Irrigation_Method"] = pd.Categorical(
        out["Irrigation_Method"], categories=IRRIGATION_ORDER, ordered=True
    )

    crop_median_yield = out.groupby("Crop")["Yield_Tonnes_Ha"].transform("median")
    out["Yield_Index"] = out["Yield_Tonnes_Ha"] / crop_median_yield
    out["Profit_per_Ha"] = out["Profit_INR"] / out["Farm_Area_Hectares"]
    out["Profit_Margin"] = out["Profit_INR"] / out["Total_Cost_INR"]
    out["Water_m3_per_Ha"] = out["Water_Used_m3"] / out["Farm_Area_Hectares"]
    out["Water_Index"] = out["Water_m3_per_Ha"] / out.groupby("Crop")["Water_m3_per_Ha"].transform("median")
    out["Is_Profitable"] = out["Profit_INR"] > 0

    if out[["Season", "Irrigation_Method"]].isna().any().any():
        raise ValueError("Unexpected Season or Irrigation_Method label in the dataset.")
    if not np.isfinite(out["Yield_Index"]).all():
        raise ValueError("Yield could not be recovered for every row.")
    return out


def load_clean_data(path: str | Path = DATA_PATH) -> pd.DataFrame:
    """Convenience wrapper: load the CSV and return the cleaned frame."""
    return clean_data(load_data(path))
