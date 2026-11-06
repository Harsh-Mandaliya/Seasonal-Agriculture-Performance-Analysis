"""Matplotlib figures for the project.

Each function takes the cleaned frame and returns a ``Figure`` so the same
chart can be saved by ``scripts/run_analysis.py``, shown in the notebook and
embedded in the Streamlit app.

Design rules used throughout: one colour per *meaning* (seasons always keep
the same colour), no dual axes, light gridlines, direct value labels only
where they help, and crop-adjusted metrics for any cross-crop comparison.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

from . import analysis as A
from .data import SEASON_ORDER

# Palette ---------------------------------------------------------------
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e1e0d9"
BLUE = "#2a78d6"
RED = "#e34948"
NEUTRAL = "#f0efec"
SEASON_COLORS = {"Kharif": "#2a78d6", "Rabi": "#eb6834", "Zaid": "#1baf7a"}
LINE_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
DIVERGING = LinearSegmentedColormap.from_list(
    "red_neutral_blue", ["#b3261e", RED, "#f3a7a5", NEUTRAL, "#9ec5f4", BLUE, "#184f95"]
)


LABELS = {
    "Rainfall_mm": "Rainfall (mm)",
    "Avg_Temperature_C": "Avg temperature (C)",
    "Humidity_pct": "Humidity (%)",
    "Sunlight_Hours_Day": "Sunlight (hours/day)",
    "Soil_pH": "Soil pH",
    "Soil_Moisture_pct": "Soil moisture (%)",
    "Nitrogen_kg_ha": "Nitrogen (kg/ha)",
    "Phosphorus_kg_ha": "Phosphorus (kg/ha)",
    "Potassium_kg_ha": "Potassium (kg/ha)",
    "Fertilizer_kg_ha": "Fertiliser (kg/ha)",
    "Pesticide_Litre_ha": "Pesticide (L/ha)",
    "Seed_Quality_Score": "Seed quality score",
    "Disease_Pest_Risk_pct": "Disease / pest risk (%)",
    "Farm_Area_Hectares": "Farm area (ha)",
}


def apply_style() -> None:
    """Project-wide matplotlib defaults."""
    plt.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "axes.edgecolor": GRID,
            "axes.labelcolor": INK_2,
            "axes.titlecolor": INK,
            "axes.titleweight": "bold",
            "axes.titlesize": 13,
            "axes.titlelocation": "left",
            "axes.labelsize": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": GRID,
            "grid.linewidth": 0.8,
            "axes.axisbelow": True,
            "xtick.color": INK_2,
            "ytick.color": INK_2,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.frameon": False,
            "legend.fontsize": 9,
            "font.size": 10,
            "figure.dpi": 110,
            "savefig.dpi": 150,
            "savefig.bbox": "tight",
        }
    )


apply_style()

_inr = FuncFormatter(lambda v, _: f"{v / 1000:,.0f}k" if abs(v) >= 1000 else f"{v:,.0f}")


def _subtitle(ax, text: str) -> None:
    ax.text(0, 1.02, text, transform=ax.transAxes, fontsize=9, color=INK_2, va="bottom")


def _title(ax, title: str, subtitle: str | None = None) -> None:
    ax.set_title(title, pad=22 if subtitle else 8)
    if subtitle:
        _subtitle(ax, subtitle)


def _reference_line(ax, value: float = 1.0, axis: str = "y", label: str | None = "crop median") -> None:
    if axis == "y":
        ax.axhline(value, color=INK_2, lw=1, ls=(0, (4, 3)), zorder=1)
        if label:
            ax.annotate(label, (1, value), xycoords=("axes fraction", "data"), xytext=(-2, 3),
                        textcoords="offset points", ha="right", fontsize=8, color=INK_2)
    else:
        ax.axvline(value, color=INK_2, lw=1, ls=(0, (4, 3)), zorder=1)


def season_yield_index(df: pd.DataFrame) -> Figure:
    """Median crop-adjusted yield by season, with the interquartile range."""
    d = df.groupby("Season", observed=True)["Yield_Index"]
    med, q1, q3 = d.median(), d.quantile(0.25), d.quantile(0.75)
    seasons = [s for s in SEASON_ORDER if s in med.index]
    fig, ax = plt.subplots(figsize=(7, 4.2))
    x = np.arange(len(seasons))
    ax.bar(x, med[seasons], width=0.55, color=[SEASON_COLORS[s] for s in seasons], zorder=2)
    ax.errorbar(x, med[seasons], yerr=[med[seasons] - q1[seasons], q3[seasons] - med[seasons]],
                fmt="none", ecolor=INK_2, elinewidth=1, capsize=4, zorder=3)
    for xi, s in zip(x, seasons):
        ax.annotate(f"{med[s]:.2f}", (xi, q3[s]), xytext=(0, 4), textcoords="offset points",
                    ha="center", fontsize=9, color=INK)
    _reference_line(ax)
    ax.set_xticks(x, seasons)
    ax.set_ylabel("Yield index (1.0 = crop median)")
    ax.grid(axis="x", visible=False)
    _title(ax, "Kharif yields highest, Zaid lowest",
           "Median crop-adjusted yield by season; whiskers show the middle 50% of farms")
    fig.tight_layout()
    return fig


def crop_season_yield(df: pd.DataFrame) -> Figure:
    """Dot plot of median yield per crop per season, each crop on its own scale."""
    m = A.crop_season_matrix(df)
    rel = m.div(m["Kharif"], axis=0) * 100
    order = rel["Zaid"].sort_values().index
    fig, ax = plt.subplots(figsize=(8, 4.8))
    y = np.arange(len(order))
    ax.hlines(y, rel.loc[order].min(axis=1), rel.loc[order].max(axis=1), color=GRID, lw=3, zorder=1)
    for s in SEASON_ORDER:
        ax.scatter(rel.loc[order, s], y, s=70, color=SEASON_COLORS[s], edgecolor=SURFACE,
                   linewidth=1.5, zorder=3, label=s)
    for yi, crop in zip(y, order):
        ax.annotate(f"{m.loc[crop, 'Kharif']:.2f} t/ha in Kharif", (100, yi), xytext=(8, 0),
                    textcoords="offset points", va="center", fontsize=8, color=INK_2)
    ax.set_yticks(y, order)
    ax.set_xlabel("Median yield, % of the same crop's Kharif yield")
    ax.set_xlim(rel.min().min() - 5, 142)
    ax.grid(axis="y", visible=False)
    ax.legend(loc="center right", title="Season", title_fontsize=9)
    _title(ax, "Every crop loses yield outside Kharif",
           "Median yield by crop and season, relative to that crop's Kharif median")
    fig.tight_layout()
    return fig


def crop_profit_per_ha(df: pd.DataFrame) -> Figure:
    """Diverging bar chart of median profit per hectare by crop."""
    cs = A.crop_summary(df).sort_values("Median_Profit_per_Ha")
    vals = cs["Median_Profit_per_Ha"]
    fig, ax = plt.subplots(figsize=(8, 4.6))
    colors = [BLUE if v >= 0 else RED for v in vals]
    ax.barh(cs.index, vals, color=colors, height=0.6, zorder=2)
    for crop, v, pct in zip(cs.index, vals, cs["Pct_Profitable"]):
        # Loss labels sit on the right of the zero line so they never collide with crop names.
        ax.annotate(f"INR {v:,.0f}  ({pct:.0f}% profitable)", (max(v, 0), crop),
                    xytext=(6, 0), textcoords="offset points",
                    ha="left", va="center", fontsize=8, color=INK)
    _reference_line(ax, 0, axis="x")
    lo, hi = vals.min(), vals.max()
    ax.set_xlim(lo * 1.6, hi * 1.45)
    ax.xaxis.set_major_formatter(_inr)
    ax.set_xlabel("Median profit per hectare (INR)")
    ax.grid(axis="y", visible=False)
    _title(ax, "Sugarcane and chilli pay; wheat, rice and maize lose money",
           "Median profit per hectare by crop (blue = profit, red = loss)")
    fig.tight_layout()
    return fig


def crop_season_profit_heatmap(df: pd.DataFrame) -> Figure:
    """Heatmap of median profit per hectare, crop x season (diverging around 0)."""
    m = A.crop_season_matrix(df, "Profit_per_Ha")
    m = m.loc[m.mean(axis=1).sort_values(ascending=False).index]
    lim = np.nanmax(np.abs(m.to_numpy()))
    fig, ax = plt.subplots(figsize=(6.6, 5))
    im = ax.imshow(m.to_numpy(), cmap=DIVERGING, norm=TwoSlopeNorm(0, -lim, lim), aspect="auto")
    ax.set_xticks(range(m.shape[1]), m.columns)
    ax.set_yticks(range(m.shape[0]), m.index)
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            v = m.iat[i, j]
            ax.text(j, i, f"{v / 1000:,.1f}k", ha="center", va="center", fontsize=9,
                    color=SURFACE if abs(v) > lim * 0.55 else INK)
    cb = fig.colorbar(im, ax=ax, shrink=0.8, format=_inr)
    cb.outline.set_visible(False)
    cb.set_label("Median profit per ha (INR)", color=INK_2)
    _title(ax, "Profit per hectare by crop and season",
           "Same crop, worse season: Zaid is the weakest column for every crop")
    fig.tight_layout()
    return fig


def irrigation_comparison(df: pd.DataFrame) -> Figure:
    """Two panels (no dual axis): water use and yield, both crop-adjusted."""
    irr = A.irrigation_summary(df)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
    panels = [
        ("Median_Water_Index", "Water per hectare (1.0 = crop median)", "Water use"),
        ("Median_Yield_Index", "Yield index (1.0 = crop median)", "Yield"),
    ]
    for ax, (col, xlabel, title) in zip(axes, panels):
        vals = irr[col]
        ax.barh(irr.index, vals, color=BLUE, height=0.55, zorder=2)
        for method, v in vals.items():
            ax.annotate(f"{v:.2f}", (v, method), xytext=(4, 0), textcoords="offset points",
                        va="center", fontsize=9, color=INK)
        _reference_line(ax, 1.0, axis="x")
        ax.set_xlim(0, vals.max() * 1.2)
        ax.set_xlabel(xlabel)
        ax.grid(axis="y", visible=False)
        ax.set_title(title, fontsize=11)
    axes[0].invert_yaxis()
    fig.suptitle("Drip irrigation: higher yield with less water than flood",
                 x=0.01, y=0.985, ha="left", fontweight="bold", fontsize=13, color=INK)
    fig.text(0.01, 0.925, "Crop-adjusted medians by irrigation method (1.0 = typical for the crop)",
             fontsize=9, color=INK_2)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    return fig


def rainfall_response(df: pd.DataFrame) -> Figure:
    """Yield index across rainfall bands, with the raw points behind."""
    rr = A.rainfall_response(df)
    d = df.dropna(subset=["Rainfall_mm"])
    fig, ax = plt.subplots(figsize=(8, 4.4))
    ax.scatter(d["Rainfall_mm"], d["Yield_Index"], s=8, color="#9ec5f4", alpha=0.45,
               linewidth=0, zorder=1, label="Individual farms")
    edges = A.RAINFALL_BANDS[:-1] + [d["Rainfall_mm"].max()]
    band_mid = {lab: (edges[i] + edges[i + 1]) / 2 for i, lab in enumerate(A.RAINFALL_LABELS)}
    centers = [band_mid[band] for band in rr.index]
    ax.fill_between(centers, rr["Q1_Yield_Index"], rr["Q3_Yield_Index"], color=BLUE, alpha=0.15,
                    lw=0, zorder=2, label="Middle 50% of farms")
    ax.plot(centers, rr["Median_Yield_Index"], color=BLUE, lw=2, marker="o", ms=7,
            markeredgecolor=SURFACE, markeredgewidth=1.5, zorder=3, label="Median by rainfall band")
    for c, (band, row) in zip(centers, rr.iterrows()):
        ax.annotate(f"{band}\n{row['Median_Yield_Index']:.2f}", (c, row["Q3_Yield_Index"]),
                    xytext=(0, 6), textcoords="offset points", ha="center", fontsize=8, color=INK)
    _reference_line(ax)
    ax.set_ylim(0, 2.6)
    ax.set_xlabel("Seasonal rainfall (mm)")
    ax.set_ylabel("Yield index (1.0 = crop median)")
    ax.legend(loc="upper left")
    _title(ax, "Yield peaks at 550-850 mm of rain",
           f"Crop-adjusted yield vs rainfall ({len(d):,} farms with rainfall recorded)")
    fig.tight_layout()
    return fig


def pest_risk_effect(df: pd.DataFrame) -> Figure:
    """Pest-risk effect on yield, shown separately within each rainfall band."""
    p = A.pest_risk_by_rainfall(df)
    fig, ax = plt.subplots(figsize=(8, 4.4))
    x = np.arange(len(p.index))
    for color, band in zip(LINE_COLORS, p.columns):
        s = p[band]
        ax.plot(x, s.to_numpy(), color=color, lw=2, marker="o", ms=7, markeredgecolor=SURFACE,
                markeredgewidth=1.5, label=f"Rainfall {band}")
        last = s.last_valid_index()
        if last is not None:
            ax.annotate(band, (list(p.index).index(last), s[last]), xytext=(8, 0),
                        textcoords="offset points", va="center", fontsize=8, color=INK_2)
    _reference_line(ax, label=None)
    ax.set_xticks(x, p.index)
    ax.set_xlim(-0.3, len(x) - 0.1)
    ax.set_xlabel("Disease / pest risk")
    ax.set_ylabel("Median yield index (1.0 = crop median)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=4)
    _title(ax, "Pest risk has no clear effect once rainfall is held fixed",
           "Median crop-adjusted yield by pest-risk band, one line per rainfall band (cells < 20 farms hidden)")
    fig.tight_layout()
    return fig


def yield_drivers(df: pd.DataFrame) -> Figure:
    """Spearman correlation of each input with crop-adjusted yield."""
    d = A.yield_drivers(df)["Spearman_vs_Yield_Index"].sort_values()
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh([LABELS.get(i, i) for i in d.index], d, color=[BLUE if v >= 0 else RED for v in d],
            height=0.6, zorder=2)
    for i, v in enumerate(d):
        ax.annotate("0.00" if abs(v) < 0.005 else f"{v:+.2f}", (v, i), xytext=(4 if v >= 0 else -4, 0), textcoords="offset points",
                    ha="left" if v >= 0 else "right", va="center", fontsize=8, color=INK)
    _reference_line(ax, 0, axis="x")
    ax.set_xlim(min(-0.15, d.min() * 1.4), d.max() * 1.25)
    ax.set_xlabel("Spearman correlation with crop-adjusted yield")
    ax.grid(axis="y", visible=False)
    _title(ax, "Moisture-related inputs are the strongest yield drivers",
           "Pest risk's positive value is confounded by rainfall (see chart 07)")
    fig.tight_layout()
    return fig


FIGURES = {
    "01_yield_index_by_season": season_yield_index,
    "02_crop_season_yield": crop_season_yield,
    "03_profit_per_ha_by_crop": crop_profit_per_ha,
    "04_profit_heatmap_crop_season": crop_season_profit_heatmap,
    "05_irrigation_water_and_yield": irrigation_comparison,
    "06_rainfall_vs_yield": rainfall_response,
    "07_pest_risk_within_rainfall": pest_risk_effect,
    "08_yield_drivers": yield_drivers,
}
