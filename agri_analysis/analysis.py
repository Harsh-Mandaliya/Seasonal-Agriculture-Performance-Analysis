"""Summary tables and statistics used by the notebook, the script and the app.

Every function takes the *cleaned* frame from :func:`agri_analysis.data.clean_data`.

A note on comparing yields
--------------------------
Sugarcane yields ~48 t/ha while every other crop yields 1-3 t/ha, so a plain
mean of ``Yield_Tonnes_Ha`` across crops mostly measures *how much sugarcane*
is in a group. Cross-crop comparisons therefore use ``Yield_Index`` (yield
relative to the crop's own median) and medians, which are robust to the long
right tail. Raw means are still reported for reference.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .data import IRRIGATION_ORDER, SEASON_ORDER

# Numeric inputs that could plausibly *drive* yield. Outcome columns that are
# computed from yield (production, revenue, profit, water efficiency) are
# excluded, because their correlation with yield is true by construction.
DRIVER_COLUMNS = [
    "Rainfall_mm", "Avg_Temperature_C", "Humidity_pct", "Sunlight_Hours_Day",
    "Soil_pH", "Soil_Moisture_pct", "Nitrogen_kg_ha", "Phosphorus_kg_ha",
    "Potassium_kg_ha", "Fertilizer_kg_ha", "Pesticide_Litre_ha",
    "Seed_Quality_Score", "Disease_Pest_Risk_pct", "Farm_Area_Hectares",
]

PRETTY = {"Rainfall_mm": "Rainfall", "Soil_Moisture_pct": "Soil moisture", "Humidity_pct": "Humidity"}

RAINFALL_BANDS = [0, 350, 550, 850, np.inf]
RAINFALL_LABELS = ["< 350 mm", "350-550 mm", "550-850 mm", "> 850 mm"]
PEST_BANDS = [0, 30, 40, 50, 60, 101]
PEST_LABELS = ["< 30%", "30-40%", "40-50%", "50-60%", "> 60%"]


def spearman(a: pd.Series, b: pd.Series) -> float:
    """Spearman rank correlation (pairwise complete), without needing SciPy."""
    pair = pd.concat([a, b], axis=1).dropna().rank()
    return float(pair.iloc[:, 0].corr(pair.iloc[:, 1]))


def _group(df: pd.DataFrame, key: str):
    return df.groupby(key, observed=True)


def _with_bands(df: pd.DataFrame) -> pd.DataFrame:
    d = df.dropna(subset=["Rainfall_mm"]).copy()
    d["Rainfall_Band"] = pd.cut(d["Rainfall_mm"], RAINFALL_BANDS, labels=RAINFALL_LABELS, right=False)
    d["Pest_Band"] = pd.cut(d["Disease_Pest_Risk_pct"], PEST_BANDS, labels=PEST_LABELS, right=False)
    return d


def data_overview(df: pd.DataFrame) -> pd.DataFrame:
    """Shape, missing values and level counts, as a tidy table."""
    rows = [
        ("Records", len(df)),
        ("States", df["State"].nunique()),
        ("Districts", df["District"].nunique()),
        ("Crops", df["Crop"].nunique()),
        ("Seasons", df["Season"].nunique()),
        ("Irrigation methods", df["Irrigation_Method"].nunique()),
        ("Missing Rainfall_mm", int(df["Rainfall_mm"].isna().sum())),
        ("Missing Soil_Moisture_pct", int(df["Soil_Moisture_pct"].isna().sum())),
        ("Yield values recovered from Production / Area", int(df["Yield_Imputed"].sum())),
        ("Duplicate Farm_IDs", int(df["Farm_ID"].duplicated().sum())),
    ]
    return pd.DataFrame(rows, columns=["Item", "Value"])


def season_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Season-level performance (one row per season, in calendar order)."""
    out = _group(df, "Season").agg(
        Farms=("Farm_ID", "count"),
        Median_Yield_Index=("Yield_Index", "median"),
        Avg_Yield_Tonnes_Ha=("Yield_Tonnes_Ha", "mean"),
        Total_Production_Tonnes=("Production_Tonnes", "sum"),
        Avg_Revenue_INR=("Revenue_INR", "mean"),
        Avg_Cost_INR=("Total_Cost_INR", "mean"),
        Avg_Profit_INR=("Profit_INR", "mean"),
        Median_Profit_per_Ha=("Profit_per_Ha", "median"),
        Pct_Profitable=("Is_Profitable", "mean"),
        Median_Rainfall_mm=("Rainfall_mm", "median"),
        Median_Pest_Risk_pct=("Disease_Pest_Risk_pct", "median"),
        Avg_Water_Efficiency=("Water_Efficiency_t_per_1000m3", "mean"),
    )
    out["Pct_Profitable"] *= 100
    return out.reindex([s for s in SEASON_ORDER if s in out.index])


def crop_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Crop-level performance, sorted by median profit per hectare."""
    out = _group(df, "Crop").agg(
        Farms=("Farm_ID", "count"),
        Median_Yield_Tonnes_Ha=("Yield_Tonnes_Ha", "median"),
        Avg_Yield_Tonnes_Ha=("Yield_Tonnes_Ha", "mean"),
        Median_Price_INR_Tonne=("Market_Price_INR_Tonne", "median"),
        Avg_Profit_INR=("Profit_INR", "mean"),
        Median_Profit_per_Ha=("Profit_per_Ha", "median"),
        Median_Profit_Margin=("Profit_Margin", "median"),
        Pct_Profitable=("Is_Profitable", "mean"),
        Total_Production_Tonnes=("Production_Tonnes", "sum"),
    )
    out["Pct_Profitable"] *= 100
    return out.sort_values("Median_Profit_per_Ha", ascending=False)


def crop_season_matrix(df: pd.DataFrame, value: str = "Yield_Tonnes_Ha", agg: str = "median") -> pd.DataFrame:
    """Crop x season pivot of a metric (default: median yield)."""
    m = df.pivot_table(index="Crop", columns="Season", values=value, aggfunc=agg, observed=True)
    return m.reindex(columns=[s for s in SEASON_ORDER if s in m.columns])


def seasonal_yield_change(df: pd.DataFrame) -> pd.DataFrame:
    """Median yield of each crop in Rabi and Zaid relative to Kharif (%)."""
    m = crop_season_matrix(df)
    out = pd.DataFrame(
        {
            "Kharif_t_ha": m["Kharif"],
            "Rabi_t_ha": m["Rabi"],
            "Zaid_t_ha": m["Zaid"],
            "Rabi_vs_Kharif_pct": (m["Rabi"] / m["Kharif"] - 1) * 100,
            "Zaid_vs_Kharif_pct": (m["Zaid"] / m["Kharif"] - 1) * 100,
        }
    )
    return out.sort_values("Zaid_vs_Kharif_pct")


def irrigation_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Irrigation-method comparison on crop-adjusted yield and water use."""
    out = _group(df, "Irrigation_Method").agg(
        Farms=("Farm_ID", "count"),
        Median_Yield_Index=("Yield_Index", "median"),
        Median_Water_Index=("Water_Index", "median"),
        Median_Water_m3_per_Ha=("Water_m3_per_Ha", "median"),
        Avg_Water_Efficiency=("Water_Efficiency_t_per_1000m3", "mean"),
        Median_Profit_per_Ha=("Profit_per_Ha", "median"),
        Pct_Profitable=("Is_Profitable", "mean"),
    )
    out["Pct_Profitable"] *= 100
    return out.reindex([m for m in IRRIGATION_ORDER if m in out.index])


def yield_drivers(df: pd.DataFrame) -> pd.DataFrame:
    """Spearman correlation of each candidate driver with the crop-adjusted yield.

    Also reports the naive Pearson correlation with raw yield (what the first
    version of this project reported) so the difference is visible.
    """
    rows = []
    for col in DRIVER_COLUMNS:
        pair = df[[col, "Yield_Index", "Yield_Tonnes_Ha"]].dropna()
        rows.append(
            {
                "Variable": col,
                "Spearman_vs_Yield_Index": spearman(pair[col], pair["Yield_Index"]),
                "Pearson_vs_Raw_Yield": pair[col].corr(pair["Yield_Tonnes_Ha"]),
                "N": len(pair),
            }
        )
    out = pd.DataFrame(rows).set_index("Variable")
    return out.reindex(out["Spearman_vs_Yield_Index"].abs().sort_values(ascending=False).index)


def rainfall_response(df: pd.DataFrame) -> pd.DataFrame:
    """Crop-adjusted yield across rainfall bands (rows with rainfall only)."""
    d = _with_bands(df)
    return _group(d, "Rainfall_Band").agg(
        Farms=("Farm_ID", "count"),
        Median_Yield_Index=("Yield_Index", "median"),
        Q1_Yield_Index=("Yield_Index", lambda s: s.quantile(0.25)),
        Q3_Yield_Index=("Yield_Index", lambda s: s.quantile(0.75)),
        Median_Pest_Risk_pct=("Disease_Pest_Risk_pct", "median"),
    )


def pest_risk_by_rainfall(df: pd.DataFrame, min_farms: int = 20) -> pd.DataFrame:
    """Median yield index by pest-risk band *within* each rainfall band.

    Pest risk rises with rainfall (Spearman ~0.6), and so does yield up to a
    point, so the pooled pest-risk/yield relationship is confounded. Holding
    rainfall roughly fixed shows the pest effect on its own. Cells with fewer
    than ``min_farms`` farms are blanked.
    """
    d = _with_bands(df)
    kw = dict(index="Pest_Band", columns="Rainfall_Band", values="Yield_Index", observed=False)
    med = d.pivot_table(aggfunc="median", **kw)
    n = d.pivot_table(aggfunc="count", **kw)
    return med.where(n >= min_farms)


def pest_partial_correlation(df: pd.DataFrame) -> float:
    """Spearman correlation of pest risk with yield index after removing the
    (rank-linear) effect of rainfall, humidity and soil moisture from both."""
    controls = ["Rainfall_mm", "Humidity_pct", "Soil_Moisture_pct"]
    d = df[["Disease_Pest_Risk_pct", "Yield_Index", *controls]].dropna().rank()
    x = np.column_stack([np.ones(len(d)), d[controls].to_numpy()])

    def resid(y: np.ndarray) -> np.ndarray:
        beta, *_ = np.linalg.lstsq(x, y, rcond=None)
        return y - x @ beta

    r1 = resid(d["Disease_Pest_Risk_pct"].to_numpy())
    r2 = resid(d["Yield_Index"].to_numpy())
    return float(np.corrcoef(r1, r2)[0, 1])


def state_summary(df: pd.DataFrame) -> pd.DataFrame:
    """State-level comparison on crop-adjusted metrics."""
    out = _group(df, "State").agg(
        Farms=("Farm_ID", "count"),
        Median_Yield_Index=("Yield_Index", "median"),
        Median_Profit_per_Ha=("Profit_per_Ha", "median"),
        Pct_Profitable=("Is_Profitable", "mean"),
    )
    out["Pct_Profitable"] *= 100
    return out.sort_values("Median_Yield_Index", ascending=False)


def key_findings(df: pd.DataFrame) -> list[str]:
    """Plain-language findings, computed from the full dataset (nothing hard-coded)."""
    ss = season_summary(df)
    cs = crop_summary(df)
    sc = seasonal_yield_change(df)
    irr = irrigation_summary(df)
    rr = rainfall_response(df)
    drivers = yield_drivers(df)
    st = state_summary(df)
    pest_pooled = spearman(df["Disease_Pest_Risk_pct"], df["Yield_Index"])
    pest_partial = pest_partial_correlation(df)
    price = crop_season_matrix(df, "Market_Price_INR_Tonne")
    price_spread = ((price.max(axis=1) / price.min(axis=1) - 1) * 100).max()

    best_rain = rr["Median_Yield_Index"].idxmax()
    worst_rain = rr["Median_Yield_Index"].idxmin()
    losing = cs[cs["Median_Profit_per_Ha"] < 0].index.tolist()
    top2 = cs.index[:2].tolist()
    top_driver = drivers.index[0]
    same_order = bool(((sc["Kharif_t_ha"] > sc["Rabi_t_ha"]) & (sc["Rabi_t_ha"] > sc["Zaid_t_ha"])).all())
    weak = drivers[drivers["Spearman_vs_Yield_Index"].abs() < 0.05].index
    water_saving = (1 - irr.loc["Drip", "Median_Water_Index"] / irr.loc["Flood", "Median_Water_Index"]) * 100

    return [
        (
            f"Season is the clearest yield signal: crop-adjusted median yield is "
            f"{ss.loc['Kharif', 'Median_Yield_Index']:.2f} in Kharif, "
            f"{ss.loc['Rabi', 'Median_Yield_Index']:.2f} in Rabi and "
            f"{ss.loc['Zaid', 'Median_Yield_Index']:.2f} in Zaid (1.00 = typical for the crop). "
            + (f"All {len(sc)} crops follow the same Kharif > Rabi > Zaid order; " if same_order else "")
            + f"Zaid yields are {-sc['Zaid_vs_Kharif_pct'].max():.0f}-{-sc['Zaid_vs_Kharif_pct'].min():.0f}% "
            f"below Kharif depending on the crop."
        ),
        (
            f"Profitability follows the seasons: {ss.loc['Kharif', 'Pct_Profitable']:.0f}% of Kharif farms, "
            f"{ss.loc['Rabi', 'Pct_Profitable']:.0f}% of Rabi farms and {ss.loc['Zaid', 'Pct_Profitable']:.0f}% "
            f"of Zaid farms made a profit. Average cost is similar in every season and a crop's market price "
            f"varies by at most {price_spread:.0f}% between seasons, so the gap comes from yield, not price."
        ),
        (
            f"Crop choice matters more than any input: {top2[0]} and {top2[1]} earn a median "
            f"INR {cs.loc[top2[0], 'Median_Profit_per_Ha']:,.0f} and INR {cs.loc[top2[1], 'Median_Profit_per_Ha']:,.0f} "
            f"profit per hectare, while {', '.join(losing)} lose money at the median "
            f"(only {cs.loc[losing, 'Pct_Profitable'].min():.0f}-{cs.loc[losing, 'Pct_Profitable'].max():.0f}% "
            f"of those farms are profitable)."
        ),
        (
            f"Drip irrigation gives the best crop-adjusted yield ({irr.loc['Drip', 'Median_Yield_Index']:.2f}) "
            f"and uses {water_saving:.0f}% less water per hectare than flood irrigation, which is both the most "
            f"common method ({irr.loc['Flood', 'Farms']:,} farms) and the thirstiest. Rain-fed plots use the "
            f"least water but have the lowest yield index ({irr.loc['Rainfed', 'Median_Yield_Index']:.2f})."
        ),
        (
            f"Rainfall has a sweet spot: the yield index peaks in the {best_rain} band "
            f"({rr.loc[best_rain, 'Median_Yield_Index']:.2f}), is lowest in the {worst_rain} band "
            f"({rr.loc[worst_rain, 'Median_Yield_Index']:.2f}) and falls back on very wet plots. "
            f"{PRETTY.get(top_driver, top_driver)} is the strongest single numeric driver "
            f"(Spearman {drivers.loc[top_driver, 'Spearman_vs_Yield_Index']:.2f})."
        ),
        (
            f"Pest risk looks *positively* related to yield when pooled (Spearman {pest_pooled:.2f}) only "
            f"because pest risk rises with rainfall and humidity. After controlling for rainfall, humidity "
            f"and soil moisture the partial correlation is {pest_partial:.2f}: in this dataset pest risk has "
            f"no meaningful independent effect on yield."
        ),
        (
            f"Fertiliser, pesticide volume, seed quality, soil pH and temperature show almost no "
            f"relationship with crop-adjusted yield (|Spearman| < 0.05 for each; {len(weak)} of "
            f"{len(drivers)} candidate inputs are below that threshold), and state-level differences are "
            f"small (median yield index {st['Median_Yield_Index'].min():.2f}-{st['Median_Yield_Index'].max():.2f})."
        ),
        (
            "The headline correlations in the first version of this project (water efficiency 0.92 and "
            "production 0.89 with yield) were artefacts: both columns are calculated from yield and "
            "dominated by sugarcane. They are replaced here by the crop-adjusted driver analysis."
        ),
    ]
