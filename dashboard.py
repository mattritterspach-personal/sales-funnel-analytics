"""
Sales Funnel Analytics — Streamlit Dashboard
Run: streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
from funnel_analysis import (
    generate_sample_data, load_data, score_leads,
    funnel_volume, stage_conversion_rates, velocity_by_stage,
    pipeline_velocity, conversion_by_source,
    plot_funnel, plot_conversion_waterfall, plot_velocity_heatmap, plot_source_performance,
)

st.set_page_config(page_title="Sales Funnel Analytics", page_icon="📊", layout="wide")

st.sidebar.title("⚙️ Settings")
data_source = st.sidebar.radio("Data source", ["Sample data", "Upload CSV"])

if data_source == "Upload CSV":
    uploaded = st.sidebar.file_uploader("Upload leads CSV", type="csv")
    df_raw = load_data(uploaded) if uploaded else generate_sample_data()
else:
    df_raw = generate_sample_data()

df_raw = score_leads(df_raw)
sources = st.sidebar.multiselect("Lead source", df_raw["lead_source"].unique(), default=list(df_raw["lead_source"].unique()))
industries = st.sidebar.multiselect("Industry", df_raw["industry"].unique(), default=list(df_raw["industry"].unique()))
sizes = st.sidebar.multiselect("Company size", df_raw["company_size"].unique(), default=list(df_raw["company_size"].unique()))
df = df_raw[df_raw["lead_source"].isin(sources) & df_raw["industry"].isin(industries) & df_raw["company_size"].isin(sizes)]

st.title("📊 Sales Funnel Analytics")
st.caption("Real-time pipeline visibility -- conversion rates, velocity, lead scoring, and source performance.")

col1, col2, col3, col4, col5 = st.columns(5)
total_leads = len(df)
won = df[df["stage"] == "Closed Won"]
win_rate = len(won) / len(df[df["stage"].isin(["Closed Won", "Closed Lost"])]) if len(df[df["stage"].isin(["Closed Won", "Closed Lost"])]) > 0 else 0
total_rev = won["deal_value"].sum()
avg_deal = won["deal_value"].mean() if len(won) > 0 else 0
pv = pipeline_velocity(df)
col1.metric("Total Leads", f"{total_leads:,}")
col2.metric("Win Rate", f"{win_rate:.1%}")
col3.metric("Total Revenue", f"${total_rev:,.0f}")
col4.metric("Avg Deal Size", f"${avg_deal:,.0f}")
col5.metric("Pipeline Velocity", f"${pv:,.0f}/day")
st.divider()
col_l, col_r = st.columns(2)
with col_l: st.plotly_chart(plot_funnel(df), use_container_width=True)
with col_r: st.plotly_chart(plot_conversion_waterfall(df), use_container_width=True)
col_l2, col_r2 = st.columns(2)
with col_l2: st.plotly_chart(plot_velocity_heatmap(df), use_container_width=True)
with col_r2: st.plotly_chart(plot_source_performance(df), use_container_width=True)
st.divider()
st.subheader("Lead Scoring")
st.dataframe(df[["lead_id", "stage", "lead_source", "industry", "company_size", "deal_value", "lead_score", "score_tier"]].sort_values("lead_score", ascending=False).head(50), use_container_width=True, hide_index=True)
st.subheader("Conversion Rates by Stage")
st.dataframe(stage_conversion_rates(df), use_container_width=True, hide_index=True)
st.subheader("Stage Velocity")
st.dataframe(velocity_by_stage(df), use_container_width=True, hide_index=True)
