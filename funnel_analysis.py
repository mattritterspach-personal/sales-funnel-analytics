"""
Sales Funnel Analysis Library
Core analysis functions for pipeline metrics, conversion rates, and lead scoring.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import Optional


# ─── Data Loading ──────────────────────────────────────────────────────────────

def load_data(path: str = "data/sample_data.csv") -> pd.DataFrame:
    """
    Load and preprocess lead/opportunity data.
    Replace this function body to connect your own CRM or database.
    """
    df = pd.read_csv(path, parse_dates=["created_date", "stage_date", "closed_date"])
    df["deal_value"] = df["deal_value"].fillna(0)
    df["days_in_stage"] = (df["stage_date"] - df["created_date"]).dt.days
    return df


def generate_sample_data(n: int = 500, seed: int = 42) -> pd.DataFrame:
    """Generate realistic sample funnel data for demo/testing."""
    rng = np.random.default_rng(seed)
    stages = ["MQL", "SQL", "Opportunity", "Proposal", "Closed Won", "Closed Lost"]
    stage_weights = [0.40, 0.25, 0.15, 0.10, 0.06, 0.04]
    sources = ["Organic Search", "Paid Search", "Content", "Referral", "Outbound", "Event"]
    industries = ["SaaS", "FinTech", "Healthcare", "E-commerce", "Manufacturing", "Other"]
    sizes = ["1-50", "51-200", "201-500", "501-2000", "2000+"]

    created = [datetime(2024, 1, 1) + timedelta(days=int(d)) for d in rng.integers(0, 365, n)]
    stage_chosen = rng.choice(stages, n, p=stage_weights)
    stage_days = rng.integers(1, 90, n)

    data = {
        "lead_id": [f"L{str(i).zfill(5)}" for i in range(n)],
        "created_date": created,
        "stage": stage_chosen,
        "stage_date": [c + timedelta(days=int(d)) for c, d in zip(created, stage_days)],
        "lead_source": rng.choice(sources, n),
        "industry": rng.choice(industries, n),
        "company_size": rng.choice(sizes, n),
        "owner": [f"Rep {rng.integers(1, 8)}" for _ in range(n)],
        "deal_value": rng.integers(5000, 200000, n) * (stage_chosen == "Closed Won").astype(int),
        "closed_date": [
            c + timedelta(days=int(d) + rng.integers(30, 120))
            if s in ["Closed Won", "Closed Lost"] else pd.NaT
            for c, d, s in zip(created, stage_days, stage_chosen)
        ],
    }
    return pd.DataFrame(data)


# ─── Funnel Metrics ────────────────────────────────────────────────────────────

STAGE_ORDER = ["MQL", "SQL", "Opportunity", "Proposal", "Closed Won"]


def funnel_volume(df: pd.DataFrame) -> pd.DataFrame:
    """Count leads at each funnel stage in order."""
    counts = df["stage"].value_counts()
    result = pd.DataFrame({
        "stage": STAGE_ORDER,
        "count": [counts.get(s, 0) for s in STAGE_ORDER],
    })
    result["conversion_from_top"] = result["count"] / result["count"].iloc[0]
    return result


def stage_conversion_rates(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate step-over-step conversion rates between adjacent stages."""
    vol = funnel_volume(df)
    rates = []
    for i in range(len(STAGE_ORDER) - 1):
        from_stage = STAGE_ORDER[i]
        to_stage = STAGE_ORDER[i + 1]
        from_count = vol.loc[vol["stage"] == from_stage, "count"].values[0]
        to_count = vol.loc[vol["stage"] == to_stage, "count"].values[0]
        rate = to_count / from_count if from_count > 0 else 0
        rates.append({
            "from_stage": from_stage,
            "to_stage": to_stage,
            "from_count": from_count,
            "to_count": to_count,
            "conversion_rate": round(rate, 4),
        })
    return pd.DataFrame(rates)


def velocity_by_stage(df: pd.DataFrame) -> pd.DataFrame:
    """Average days spent at each stage."""
    return (
        df.groupby("stage")["days_in_stage"]
        .agg(["mean", "median", "std", "count"])
        .rename(columns={"mean": "avg_days", "median": "median_days", "std": "std_days", "count": "n"})
        .reindex(STAGE_ORDER)
        .reset_index()
    )


def pipeline_velocity(df: pd.DataFrame) -> float:
    """
    Pipeline Velocity = (# Opportunities × Win Rate × Avg Deal Size) / Sales Cycle Length
    Returns revenue per day.
    """
    opps = len(df[df["stage"].isin(["Opportunity", "Proposal", "Closed Won", "Closed Lost"])])
    won = df[df["stage"] == "Closed Won"]
    total_closeable = len(df[df["stage"].isin(["Closed Won", "Closed Lost"])])
    win_rate = len(won) / total_closeable if total_closeable > 0 else 0
    avg_deal = won["deal_value"].mean() if len(won) > 0 else 0
    closed = df.dropna(subset=["closed_date", "created_date"])
    cycle = (closed["closed_date"] - closed["created_date"]).dt.days.mean() if len(closed) > 0 else 90
    return (opps * win_rate * avg_deal) / cycle if cycle > 0 else 0


def conversion_by_source(df: pd.DataFrame) -> pd.DataFrame:
    """Win rate broken down by lead source."""
    won = df[df["stage"] == "Closed Won"].groupby("lead_source").size().rename("won")
    total = df.groupby("lead_source").size().rename("total")
    result = pd.concat([total, won], axis=1).fillna(0)
    result["win_rate"] = result["won"] / result["total"]
    result["avg_deal"] = df[df["stage"] == "Closed Won"].groupby("lead_source")["deal_value"].mean()
    return result.reset_index().sort_values("win_rate", ascending=False)


# ─── Lead Scoring ──────────────────────────────────────────────────────────────

INDUSTRY_SCORE = {"SaaS": 10, "FinTech": 9, "Healthcare": 8, "E-commerce": 7, "Manufacturing": 5, "Other": 3}
SIZE_SCORE = {"2000+": 10, "501-2000": 8, "201-500": 6, "51-200": 4, "1-50": 2}
SOURCE_SCORE = {"Referral": 10, "Outbound": 8, "Content": 7, "Event": 6, "Organic Search": 5, "Paid Search": 4}

WEIGHTS = {"industry": 0.35, "company_size": 0.30, "lead_source": 0.35}


def score_leads(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute a weighted lead score (0-100) based on firmographic + source signals.
    Extend INDUSTRY_SCORE, SIZE_SCORE, SOURCE_SCORE dicts to fit your ICP.
    """
    df = df.copy()
    df["industry_score"] = df["industry"].map(INDUSTRY_SCORE).fillna(3)
    df["size_score"] = df["company_size"].map(SIZE_SCORE).fillna(3)
    df["source_score"] = df["lead_source"].map(SOURCE_SCORE).fillna(3)
    df["lead_score"] = (
        df["industry_score"] * WEIGHTS["industry"]
        + df["size_score"] * WEIGHTS["company_size"]
        + df["source_score"] * WEIGHTS["lead_source"]
    ) * 10  # scale to 100
    df["score_tier"] = pd.cut(df["lead_score"], bins=[0, 40, 65, 80, 100], labels=["C", "B", "A", "S"])
    return df


# ─── Charts ────────────────────────────────────────────────────────────────────

def plot_funnel(df: pd.DataFrame) -> go.Figure:
    """Plotly funnel chart showing volume at each stage."""
    vol = funnel_volume(df)
    fig = go.Figure(go.Funnel(
        y=vol["stage"],
        x=vol["count"],
        textinfo="value+percent initial",
        marker=dict(color=["#4F46E5", "#7C3AED", "#A855F7", "#C084FC", "#E9D5FF"]),
    ))
    fig.update_layout(title="Sales Funnel — Lead Volume by Stage", height=420)
    return fig


def plot_conversion_waterfall(df: pd.DataFrame) -> go.Figure:
    """Waterfall chart of step-over-step conversion rates."""
    rates = stage_conversion_rates(df)
    fig = go.Figure(go.Bar(
        x=[f"{r['from_stage']} → {r['to_stage']}" for _, r in rates.iterrows()],
        y=rates["conversion_rate"],
        text=[f"{r['conversion_rate']:.1%}" for _, r in rates.iterrows()],
        textposition="outside",
        marker_color="#4F46E5",
    ))
    fig.update_layout(
        title="Step-over-Step Conversion Rates",
        yaxis_tickformat=".0%",
        yaxis_range=[0, 1],
        height=380,
    )
    return fig


def plot_velocity_heatmap(df: pd.DataFrame) -> go.Figure:
    """Bar chart of average days per stage."""
    vel = velocity_by_stage(df).dropna(subset=["avg_days"])
    fig = px.bar(
        vel, x="stage", y="avg_days",
        error_y="std_days",
        color="avg_days",
        color_continuous_scale="Purples",
        labels={"avg_days": "Avg Days", "stage": "Stage"},
        title="Average Days per Funnel Stage",
    )
    fig.update_layout(height=380, coloraxis_showscale=False)
    return fig


def plot_source_performance(df: pd.DataFrame) -> go.Figure:
    """Scatter: win rate vs avg deal value by lead source."""
    src = conversion_by_source(df).dropna()
    fig = px.scatter(
        src, x="win_rate", y="avg_deal",
        size="total", color="lead_source",
        text="lead_source",
        labels={"win_rate": "Win Rate", "avg_deal": "Avg Deal Value ($)", "total": "Total Leads"},
        title="Lead Source Performance: Win Rate vs Deal Value",
    )
    fig.update_traces(textposition="top center")
    fig.update_xaxes(tickformat=".0%")
    fig.update_layout(height=420, showlegend=False)
    return fig
