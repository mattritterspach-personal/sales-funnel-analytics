# Sales Funnel Analytics

A production-ready Python toolkit for tracking, visualizing, and optimizing B2B sales funnels. Includes a Streamlit dashboard, SQL query library, and sample data.

## What's Inside

| File | Description |
|------|-------------|
| `dashboard.py` | Interactive Streamlit dashboard |
| `funnel_analysis.py` | Core analysis library (Pandas/Plotly) |
| `sql/funnel_queries.sql` | SQL queries for CRM/data warehouse |
| `data/sample_data.csv` | Sample lead/opportunity data |
| `requirements.txt` | Python dependencies |

## Features

- **Stage conversion rates** — MQL → SQL → Opportunity → Closed Won waterfall
- **Velocity tracking** — average days per stage, bottleneck identification
- **Lead scoring model** — weighted scoring by firmographic + behavioral signals
- **Cohort analysis** — conversion rates by lead source, month, rep, or segment
- **Revenue forecasting** — pipeline-weighted and stage-adjusted projections

## Quick Start

```bash
pip install -r requirements.txt
streamlit run dashboard.py
```

The dashboard runs at `http://localhost:8501` and loads `data/sample_data.csv` by default. Point it at your own CSV or connect a database by editing the `load_data()` function in `funnel_analysis.py`.

## Connecting Your Data

The analysis expects a DataFrame with these columns:

```
lead_id, created_date, stage, stage_date, lead_source,
company_size, industry, owner, deal_value, closed_date
```

Edit `funnel_analysis.py → load_data()` to connect your CRM (Salesforce, HubSpot, etc.).

## SQL Queries

`sql/funnel_queries.sql` contains ready-to-run queries for:
- Funnel volume by stage and time period
- Conversion rate by lead source
- Average sales cycle length
- Pipeline velocity (deals × conversion rate × deal size / cycle length)
- Reps leaderboard

## License

MIT
