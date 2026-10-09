-- 01_customer_churn.sql
-- Basic customer and churn KPIs

SELECT
    COUNT(*) AS customers,
    SUM(is_churn) AS churned_customers,
    COUNT(*) - SUM(is_churn) AS retained_customers,
    ROUND(100.0 * AVG(is_churn), 2) AS churn_rate_pct
FROM churn_labels;
-- Churn rate by gender

SELECT
    COALESCE(m.gender, 'Unknown') AS gender,
    COUNT(*) AS customers,
    SUM(c.is_churn) AS churned_customers,
    ROUND(100.0 * AVG(c.is_churn), 2) AS churn_rate_pct
FROM churn_labels c
JOIN members m
    ON c.msno = m.msno
GROUP BY COALESCE(m.gender, 'Unknown')
ORDER BY churn_rate_pct DESC;
-- Churn rate by age group
-- Invalid/outlier ages are classified as Unknown

SELECT
    CASE
        WHEN m.bd BETWEEN 13 AND 17 THEN '13-17'
        WHEN m.bd BETWEEN 18 AND 24 THEN '18-24'
        WHEN m.bd BETWEEN 25 AND 34 THEN '25-34'
        WHEN m.bd BETWEEN 35 AND 44 THEN '35-44'
        WHEN m.bd BETWEEN 45 AND 54 THEN '45-54'
        WHEN m.bd >= 55 AND m.bd <= 100 THEN '55+'
        ELSE 'Unknown'
    END AS age_group,
    COUNT(*) AS customers,
    SUM(c.is_churn) AS churned_customers,
    ROUND(100.0 * AVG(c.is_churn), 2) AS churn_rate_pct
FROM churn_labels c
JOIN members m
    ON c.msno = m.msno
GROUP BY age_group
ORDER BY
    CASE age_group
        WHEN '13-17' THEN 1
        WHEN '18-24' THEN 2
        WHEN '25-34' THEN 3
        WHEN '35-44' THEN 4
        WHEN '45-54' THEN 5
        WHEN '55+' THEN 6
        ELSE 7
    END;
    -- Churn rate by auto-renewal status

SELECT
    CASE
        WHEN t.is_auto_renew = 1 THEN 'Auto-renew'
        WHEN t.is_auto_renew = 0 THEN 'Manual'
        ELSE 'Unknown'
    END AS auto_renew_status,
    COUNT(DISTINCT c.msno) AS customers,
    COUNT(DISTINCT CASE WHEN c.is_churn = 1 THEN c.msno END) AS churned_customers,
    ROUND(
        100.0 * COUNT(DISTINCT CASE WHEN c.is_churn = 1 THEN c.msno END)
        / COUNT(DISTINCT c.msno),
        2
    ) AS churn_rate_pct
FROM churn_labels c
JOIN transactions t
    ON c.msno = t.msno
GROUP BY auto_renew_status
ORDER BY churn_rate_pct DESC;
-- Churn rate by payment plan duration

SELECT
    t.payment_plan_days,
    COUNT(DISTINCT c.msno) AS customers,
    COUNT(DISTINCT CASE WHEN c.is_churn = 1 THEN c.msno END) AS churned_customers,
    ROUND(
        100.0 * COUNT(DISTINCT CASE WHEN c.is_churn = 1 THEN c.msno END)
        / COUNT(DISTINCT c.msno),
        2
    ) AS churn_rate_pct
FROM churn_labels c
JOIN transactions t
    ON c.msno = t.msno
WHERE t.payment_plan_days IS NOT NULL
GROUP BY t.payment_plan_days
ORDER BY customers DESC;

-- Latest transaction for each customer

WITH latest_transaction AS (
    SELECT
        t.*,
        ROW_NUMBER() OVER (
            PARTITION BY t.msno
            ORDER BY t.transaction_date DESC, t.transaction_id DESC
        ) AS rn
    FROM transactions t
)
SELECT
    COUNT(*) AS customers,
    SUM(c.is_churn) AS churned_customers,
    ROUND(100.0 * AVG(c.is_churn), 2) AS churn_rate_pct
FROM churn_labels c
JOIN latest_transaction t
    ON c.msno = t.msno
WHERE t.rn = 1;
-- Churn rate by latest auto-renewal status

WITH latest_transaction AS (
    SELECT
        t.*,
        ROW_NUMBER() OVER (
            PARTITION BY t.msno
            ORDER BY t.transaction_date DESC, t.transaction_id DESC
        ) AS rn
    FROM transactions t
)
SELECT
    CASE
        WHEN t.is_auto_renew = 1 THEN 'Auto-renew'
        WHEN t.is_auto_renew = 0 THEN 'Manual'
        ELSE 'Unknown'
    END AS auto_renew_status,
    COUNT(*) AS customers,
    SUM(c.is_churn) AS churned_customers,
    ROUND(100.0 * AVG(c.is_churn), 2) AS churn_rate_pct
FROM churn_labels c
JOIN latest_transaction t
    ON c.msno = t.msno
WHERE t.rn = 1
GROUP BY auto_renew_status
ORDER BY churn_rate_pct DESC;
-- Engagement profile: churned vs retained customers

WITH engagement AS (
    SELECT
        msno,
        COUNT(*) AS active_days,
        SUM(num_unq) AS total_unique_songs,
        SUM(total_secs) AS total_listening_secs
    FROM user_logs_daily
    GROUP BY msno
)
SELECT
    CASE
        WHEN c.is_churn = 1 THEN 'Churned'
        ELSE 'Retained'
    END AS customer_status,
    COUNT(*) AS customers,
    ROUND(AVG(e.active_days), 2) AS avg_active_days,
    ROUND(AVG(e.total_unique_songs), 2) AS avg_unique_songs,
    ROUND(AVG(e.total_listening_secs), 2) AS avg_listening_secs
FROM churn_labels c
JOIN engagement e
    ON c.msno = e.msno
GROUP BY c.is_churn
ORDER BY c.is_churn DESC;

-- Engagement profile including customers with no usage records

WITH engagement AS (
    SELECT
        msno,
        COUNT(*) AS active_days,
        SUM(num_unq) AS total_unique_songs,
        SUM(total_secs) AS total_listening_secs
    FROM user_logs_daily
    GROUP BY msno
)
SELECT
    CASE
        WHEN c.is_churn = 1 THEN 'Churned'
        ELSE 'Retained'
    END AS customer_status,
    COUNT(*) AS customers,
    ROUND(AVG(COALESCE(e.active_days, 0)), 2) AS avg_active_days,
    ROUND(AVG(COALESCE(e.total_unique_songs, 0)), 2) AS avg_unique_songs,
    ROUND(AVG(COALESCE(e.total_listening_secs, 0)), 2) AS avg_listening_secs,
    SUM(CASE WHEN e.msno IS NULL THEN 1 ELSE 0 END) AS no_usage_customers
FROM churn_labels c
LEFT JOIN engagement e
    ON c.msno = e.msno
GROUP BY c.is_churn
ORDER BY c.is_churn DESC;

