import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Seasonal Agriculture Performance Analysis", layout="wide")

@st.cache_data
def load_data():
    return pd.read_csv("data/agriculture_data.csv")

df = load_data()

st.title("🌾 Seasonal Agriculture Performance Analysis")
st.caption("VOIS AICTE Data Analytics Major Project")

st.sidebar.header("Filters")
states = st.sidebar.multiselect("State", sorted(df["State"].dropna().unique()), default=sorted(df["State"].dropna().unique()))
seasons = st.sidebar.multiselect("Season", sorted(df["Season"].dropna().unique()), default=sorted(df["Season"].dropna().unique()))
crops = st.sidebar.multiselect("Crop", sorted(df["Crop"].dropna().unique()), default=sorted(df["Crop"].dropna().unique()))

f = df[df["State"].isin(states) & df["Season"].isin(seasons) & df["Crop"].isin(crops)]

c1,c2,c3,c4 = st.columns(4)
c1.metric("Farms", f["Farm_ID"].nunique())
c2.metric("Avg Yield", f"{f['Yield_Tonnes_Ha'].mean():.2f} t/ha")
c3.metric("Avg Revenue", f"₹{f['Revenue_INR'].mean():,.0f}")
c4.metric("Avg Profit", f"₹{f['Profit_INR'].mean():,.0f}")

st.subheader("Seasonal Performance")
season = f.groupby("Season").agg(
    Yield=("Yield_Tonnes_Ha","mean"),
    Profit=("Profit_INR","mean"),
    Production=("Production_Tonnes","sum")
).reset_index()

col1,col2 = st.columns(2)
with col1:
    fig, ax = plt.subplots()
    ax.bar(season["Season"], season["Yield"])
    ax.set_ylabel("Tonnes/Ha")
    ax.set_title("Average Yield by Season")
    st.pyplot(fig, clear_figure=True)
with col2:
    fig, ax = plt.subplots()
    ax.bar(season["Season"], season["Profit"]/1e5)
    ax.set_ylabel("INR Lakhs")
    ax.set_title("Average Profit by Season")
    st.pyplot(fig, clear_figure=True)

st.subheader("Crop Performance")
crop = f.groupby("Crop").agg(
    Avg_Yield=("Yield_Tonnes_Ha","mean"),
    Avg_Profit=("Profit_INR","mean")
).sort_values("Avg_Profit", ascending=False).head(10)
st.dataframe(crop.style.format({"Avg_Yield":"{:.2f}", "Avg_Profit":"₹{:,.0f}"}), use_container_width=True)

st.subheader("Resource & Risk Analysis")
col3,col4 = st.columns(2)
with col3:
    irr = f.groupby("Irrigation_Method")["Water_Efficiency_t_per_1000m3"].mean().sort_values()
    fig, ax = plt.subplots()
    ax.barh(irr.index, irr.values)
    ax.set_xlabel("Tonnes per 1000 m³")
    ax.set_title("Water Efficiency by Irrigation Method")
    st.pyplot(fig, clear_figure=True)
with col4:
    fig, ax = plt.subplots()
    ax.scatter(f["Disease_Pest_Risk_pct"], f["Yield_Tonnes_Ha"], alpha=0.35)
    ax.set_xlabel("Disease/Pest Risk (%)")
    ax.set_ylabel("Yield (Tonnes/Ha)")
    ax.set_title("Pest Risk vs Yield")
    st.pyplot(fig, clear_figure=True)

st.subheader("Filtered Data")
st.dataframe(f.head(500), use_container_width=True)
