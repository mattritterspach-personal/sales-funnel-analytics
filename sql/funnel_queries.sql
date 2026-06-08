-- ============================================================
-- Sales Funnel SQL Query Library
-- Tested on PostgreSQL / BigQuery / Snowflake (minor dialect tweaks may be needed)
-- ============================================================


-- ─── 1. Funnel Volume by Stage ────────────────────────────────────────────────
SELECT
    stage,
    COUNT(*) AS lead_count,
    COUNT(*) * 1.0 / SUM(COUNT(*)) OVER () AS pct_of_total
FROM leads
GROUP BY stage
ORDER BY
    CASE stage
        WHEN 'MQL'         THEN 1
        WHEN 'SQL'         THEN 2
        WHEN 'Opportunity' THEN 3
        WHEN 'Proposal'    THEN 4
        WHEN 'Closed Won'  THEN 5
        WHEN 'Closed Lost' THEN 6
    END;


-- ─── 2. Step-over-Step Conversion Rates ──────────────────────────────────────
WITH stage_counts AS (
    SELECT
        stage,
        COUNT(*) AS cnt,
        ROW_NUMBER() OVER (ORDER BY
            CASE stage
                WHEN 'MQL'         THEN 1
                WHEN 'SQL'         THEN 2
                WHEN 'Opportunity' THEN 3
                WHEN 'Proposal'    THEN 4
                WHEN 'Closed Won'  THEN 5
            END
        ) AS rn
    FROM leads
    WHERE stage NOT IN ('Closed Lost')
    GROUP BY stage
)
SELECT
    a.stage       AS from_stage,
    b.stage       AS to_stage,
    a.cnt         AS from_count,
    b.cnt         AS to_count,
    ROUND(b.cnt * 1.0 / NULLIF(a.cnt, 0), 4) AS conversion_rate
FROM stage_counts a
JOIN stage_counts b ON b.rn = a.rn + 1;


-- ─── 3. Average Sales Cycle Length ───────────────────────────────────────────
SELECT
    lead_source,
    COUNT(*) AS closed_deals,
    ROUND(AVG(DATEDIFF('day', created_date, closed_date)), 1) AS avg_cycle_days,
    ROUND(MEDIAN(DATEDIFF('day', created_date, closed_date)), 1) AS median_cycle_days
FROM leads
WHERE stage IN ('Closed Won', 'Closed Lost')
  AND closed_date IS NOT NULL
GROUP BY lead_source
ORDER BY avg_cycle_days;


-- ─── 4. Pipeline Velocity ────────────────────────────────────────────────────
-- Revenue per day = (Opportunities × Win Rate × Avg Deal) / Avg Cycle Days
WITH metrics AS (
    SELECT
        COUNT(*) FILTER (WHERE stage IN ('Opportunity','Proposal','Closed Won','Closed Lost')) AS opportunities,
        COUNT(*) FILTER (WHERE stage = 'Closed Won') * 1.0
            / NULLIF(COUNT(*) FILTER (WHERE stage IN ('Closed Won','Closed Lost')), 0)        AS win_rate,
        AVG(deal_value) FILTER (WHERE stage = 'Closed Won')                                   AS avg_deal_value,
        AVG(DATEDIFF('day', created_date, closed_date))
            FILTER (WHERE closed_date IS NOT NULL)                                            AS avg_cycle_days
    FROM leads
)
SELECT
    opportunities,
    ROUND(win_rate, 4)         AS win_rate,
    ROUND(avg_deal_value, 2)   AS avg_deal_value,
    ROUND(avg_cycle_days, 1)   AS avg_cycle_days,
    ROUND(
        (opportunities * win_rate * avg_deal_value) / NULLIF(avg_cycle_days, 0), 2
    )                          AS pipeline_velocity_per_day
FROM metrics;


-- ─── 5. Conversion Rate by Lead Source ────────────────────────────────────────
SELECT
    lead_source,
    COUNT(*)                                                              AS total_leads,
    COUNT(*) FILTER (WHERE stage = 'Closed Won')                         AS won,
    ROUND(
        COUNT(*) FILTER (WHERE stage = 'Closed Won') * 1.0
        / NULLIF(COUNT(*) FILTER (WHERE stage IN ('Closed Won','Closed Lost')), 0),
    4)                                                                    AS win_rate,
    ROUND(AVG(deal_value) FILTER (WHERE stage = 'Closed Won'), 2)        AS avg_deal_value,
    ROUND(SUM(deal_value) FILTER (WHERE stage = 'Closed Won'), 2)        AS total_revenue
FROM leads
GROUP BY lead_source
ORDER BY total_revenue DESC;


-- ─── 6. Rep Performance Leaderboard ──────────────────────────────────────────
SELECT
    owner                                                                    AS rep,
    COUNT(*)                                                                 AS total_leads,
    COUNT(*) FILTER (WHERE stage = 'Closed Won')                            AS deals_won,
    ROUND(
        COUNT(*) FILTER (WHERE stage = 'Closed Won') * 1.0
        / NULLIF(COUNT(*) FILTER (WHERE stage IN ('Closed Won','Closed Lost')), 0),
    4)                                                                       AS win_rate,
    ROUND(SUM(deal_value) FILTER (WHERE stage = 'Closed Won'), 2)           AS total_revenue,
    ROUND(AVG(deal_value) FILTER (WHERE stage = 'Closed Won'), 2)           AS avg_deal_value,
    ROUND(AVG(DATEDIFF('day', created_date, closed_date))
        FILTER (WHERE stage IN ('Closed Won','Closed Lost')
            AND closed_date IS NOT NULL), 1)                                 AS avg_cycle_days
FROM leads
GROUP BY owner
ORDER BY total_revenue DESC;


-- ─── 7. Monthly Funnel Trends ─────────────────────────────────────────────────
SELECT
    DATE_TRUNC('month', created_date) AS month,
    stage,
    COUNT(*)                           AS lead_count
FROM leads
GROUP BY 1, 2
ORDER BY 1, 3 DESC;


-- ─── 8. Cohort: Win Rate by Industry and Company Size ─────────────────────────
SELECT
    industry,
    company_size,
    COUNT(*)                                                              AS total,
    COUNT(*) FILTER (WHERE stage = 'Closed Won')                         AS won,
    ROUND(
        COUNT(*) FILTER (WHERE stage = 'Closed Won') * 1.0
        / NULLIF(COUNT(*) FILTER (WHERE stage IN ('Closed Won','Closed Lost')), 0),
    4)                                                                    AS win_rate
FROM leads
GROUP BY industry, company_size
ORDER BY win_rate DESC;
