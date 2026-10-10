-- UNEXECUTED MIGRATION TEMPLATE. Substitute YOUR_PERSONAL_PROJECT explicitly.
CREATE SCHEMA IF NOT EXISTS `YOUR_PERSONAL_PROJECT.impactguard` OPTIONS(location='US');
CREATE TABLE IF NOT EXISTS `YOUR_PERSONAL_PROJECT.impactguard.events` (
  event_id STRING NOT NULL, timestamp TIMESTAMP NOT NULL, tenant_id STRING NOT NULL,
  source STRING, event_type STRING, session_id STRING, customer_id STRING,
  browser STRING, country STRING, payment_method STRING, release STRING,
  amount NUMERIC, is_synthetic BOOL, payload JSON
) PARTITION BY DATE(timestamp) CLUSTER BY tenant_id, event_type, browser;
CREATE TABLE IF NOT EXISTS `YOUR_PERSONAL_PROJECT.impactguard.orders` (
  order_id STRING, timestamp TIMESTAMP, tenant_id STRING, session_id STRING,
  revenue NUMERIC, product_cost NUMERIC, coupons ARRAY<STRING>, is_synthetic BOOL
) PARTITION BY DATE(timestamp) CLUSTER BY tenant_id;
CREATE TABLE IF NOT EXISTS `YOUR_PERSONAL_PROJECT.impactguard.deployments` (
  deployment_id STRING, timestamp TIMESTAMP, tenant_id STRING, service STRING,
  version STRING, repository STRING, commit_sha STRING, changed_components ARRAY<STRING>, is_synthetic BOOL
) PARTITION BY DATE(timestamp) CLUSTER BY tenant_id, service;
CREATE TABLE IF NOT EXISTS `YOUR_PERSONAL_PROJECT.impactguard.support_tickets` (
  ticket_id STRING, timestamp TIMESTAMP, tenant_id STRING, customer_id STRING,
  subject STRING, body STRING, journey STRING, is_synthetic BOOL
) PARTITION BY DATE(timestamp) CLUSTER BY tenant_id;
CREATE TABLE IF NOT EXISTS `YOUR_PERSONAL_PROJECT.impactguard.metric_snapshots` (
  timestamp TIMESTAMP, tenant_id STRING, browser STRING, payment_method STRING,
  sessions INT64, conversion_rate FLOAT64, revenue NUMERIC, is_synthetic BOOL
) PARTITION BY DATE(timestamp) CLUSTER BY tenant_id;
CREATE TABLE IF NOT EXISTS `YOUR_PERSONAL_PROJECT.impactguard.findings` (
  finding_id STRING, timestamp TIMESTAMP, tenant_id STRING, status STRING,
  severity STRING, exposure NUMERIC, exposure_unit STRING, evidence JSON, investigation JSON
) PARTITION BY DATE(timestamp) CLUSTER BY tenant_id, status;

CREATE OR REPLACE VIEW `YOUR_PERSONAL_PROJECT.impactguard.hourly_checkout_metrics` AS
WITH deduplicated AS (
  SELECT * FROM `YOUR_PERSONAL_PROJECT.impactguard.events`
  QUALIFY ROW_NUMBER() OVER (PARTITION BY tenant_id,event_id ORDER BY timestamp DESC)=1
), sessions AS (
  SELECT tenant_id, session_id, browser, payment_method, is_synthetic,
    TIMESTAMP_TRUNC(MIN(timestamp),HOUR) AS timestamp,
    MAX(IF(event_type IN ('checkout_completed','order_created'),1,0)) AS success,
    MAX(IF(event_type IN ('checkout_completed','order_created'),amount,0)) AS revenue
  FROM deduplicated WHERE session_id IS NOT NULL
  GROUP BY tenant_id,session_id,browser,payment_method,is_synthetic
)
SELECT timestamp, tenant_id, browser, payment_method, is_synthetic,
  COUNT(*) AS sessions, AVG(success) AS conversion_rate, SUM(revenue) AS revenue
FROM sessions GROUP BY timestamp,tenant_id,browser,payment_method,is_synthetic;

-- Run only after populating regularly spaced metric snapshots with sufficient history.
-- Filter tenant and is_synthetic in a production workflow, never mix them.
SELECT * FROM AI.DETECT_ANOMALIES(
  (SELECT *, CAST(is_synthetic AS INT64) AS synthetic_series_id
   FROM `YOUR_PERSONAL_PROJECT.impactguard.metric_snapshots`),
  data_col => 'conversion_rate', timestamp_col => 'timestamp',
  id_cols => ['tenant_id','browser','payment_method','synthetic_series_id'],
  target_last_n_points => 12
);
