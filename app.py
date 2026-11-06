"""Interactive dashboard for the Seasonal Agriculture Performance Analysis.

Run from the project root:

    streamlit run app.py
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # Streamlit renders figures itself; avoid GUI backends

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from agri_analysis import analysis as A
from agri_analysis import plots
from agri_analysis.data import IRRIGATION_ORDER, SEASON_ORDER, load_clean_data

st.set_page_config(page_title="Seasonal Agriculture Performance Analysis", page_icon="🌾", layout="wide")

MIN_ROWS = 30  # below this, medians are too noisy to chart


@st.cache_data
def get_data() -> pd.DataFrame:
    return load_clean_data()


def show(fig) -> None:
    st.pyplot(fig, clear_figure=True)
    plt.close(fig)


def table(df: pd.DataFrame, fmt: dict[str, str] | None = None) -> None:
    st.dataframe(df.style.format(fmt or {}, precision=2), width="stretch")


df = get_data()

# Sidebar filters ---------------------------------------------------------
st.sidebar.header("Filters")
all_states = sorted(df["State"].unique())
all_crops = sorted(df["Crop"].unique())
states = st.sidebar.multiselect("State", all_states, default=all_states)
seasons = st.sidebar.multiselect("Season", SEASON_ORDER, default=SEASON_ORDER)
crops = st.sidebar.multiselect("Crop", all_crops, default=all_crops)
methods = st.sidebar.multiselect("Irrigation method", IRRIGATION_ORDER, default=IRRIGATION_ORDER)
st.sidebar.caption(
    "Yield index = a farm's yield divided by the median yield of the same crop, "
    "so 1.0 is typical for that crop. It lets sugarcane (~48 t/ha) and pulses (~1 t/ha) "
    "be compared fairly."
)

f = df[
    df["State"].isin(states)
    & df["Season"].isin(seasons)
    & df["Crop"].isin(crops)
    & df["Irrigation_Method"].isin(methods)
]

st.title("🌾 Seasonal Agriculture Performance Analysis")
st.caption(f"{len(f):,} of {len(df):,} farm records match the current filters.")

if f.empty:
    st.warning("No records match the selected filters. Widen the selection in the sidebar.")
    st.stop()

# KPIs --------------------------------------------------------------------
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Farms", f"{f['Farm_ID'].nunique():,}")
c2.metric("Yield index (median)", f"{f['Yield_Index'].median():.2f}")
c3.metric("Profit / ha (median)", f"₹{f['Profit_per_Ha'].median():,.0f}")
c4.metric("Profitable", f"{f['Is_Profitable'].mean() * 100:.0f}%")
c5.metric("Water / ha (median)", f"{f['Water_m3_per_Ha'].median():,.0f} m³")

small = len(f) < MIN_ROWS
if small:
    st.info(f"Fewer than {MIN_ROWS} records selected - charts are hidden because medians would be unreliable.")

tab_season, tab_crop, tab_water, tab_weather, tab_data = st.tabs(
    ["Seasons", "Crops", "Irrigation & water", "Weather & pest risk", "Data"]
)

with tab_season:
    if not small:
        col1, col2 = st.columns(2)
        with col1:
            show(plots.season_yield_index(f))
        with col2:
            if {"Kharif", "Rabi", "Zaid"} <= set(f["Season"].unique()):
                show(plots.crop_season_yield(f))
            else:
                st.info("Select all three seasons to compare each crop against its Kharif yield.")
    table(
        A.season_summary(f),
        {"Avg_Revenue_INR": "₹{:,.0f}", "Avg_Cost_INR": "₹{:,.0f}", "Avg_Profit_INR": "₹{:,.0f}",
         "Median_Profit_per_Ha": "₹{:,.0f}", "Pct_Profitable": "{:.0f}%"},
    )

with tab_crop:
    if not small:
        col1, col2 = st.columns(2)
        with col1:
            show(plots.crop_profit_per_ha(f))
        with col2:
            show(plots.crop_season_profit_heatmap(f))
    table(
        A.crop_summary(f),
        {"Avg_Profit_INR": "₹{:,.0f}", "Median_Profit_per_Ha": "₹{:,.0f}",
         "Median_Price_INR_Tonne": "₹{:,.0f}", "Pct_Profitable": "{:.0f}%", "Median_Profit_Margin": "{:.0%}"},
    )

with tab_water:
    if not small:
        show(plots.irrigation_comparison(f))
    table(A.irrigation_summary(f), {"Median_Profit_per_Ha": "₹{:,.0f}", "Pct_Profitable": "{:.0f}%"})

with tab_weather:
    if not small:
        col1, col2 = st.columns(2)
        with col1:
            show(plots.rainfall_response(f))
        with col2:
            show(plots.yield_drivers(f))
        show(plots.pest_risk_effect(f))
    table(A.yield_drivers(f))

with tab_data:
    st.download_button(
        "Download filtered data (CSV)",
        f.to_csv(index=False).encode("utf-8"),
        file_name="agriculture_filtered.csv",
        mime="text/csv",
    )
    st.dataframe(f.head(500), width="stretch")
    st.caption("Showing the first 500 matching rows.")

with st.expander("Key findings (full dataset)"):
    for i, finding in enumerate(A.key_findings(df), 1):
        st.markdown(f"{i}. {finding}")
