-- Task 1: BigQuery Data Quality Validation

-- 1. Row Count Validation

SELECT 'calendar' AS table_name, COUNT(*) AS row_count
FROM `fresh-yen-508710-a0.m5_raw.Calendar`

UNION ALL

SELECT 'sales_train_validation', COUNT(*)
FROM `fresh-yen-508710-a0.m5_raw.sales_train_validation`

UNION ALL

SELECT 'sales_train_evaluation', COUNT(*)
FROM `fresh-yen-508710-a0.m5_raw.sales_train_evaluation`

UNION ALL

SELECT 'sell_prices', COUNT(*)
FROM `fresh-yen-508710-a0.m5_raw.sell_prices`

UNION ALL

SELECT 'sample_submission', COUNT(*)
FROM `fresh-yen-508710-a0.m5_raw.sample_submission`;


-- 2. Sales ID Validation

SELECT
  'sales_train_validation' AS table_name,
  COUNT(*) AS total_rows,
  COUNTIF(id IS NULL) AS null_ids,
  COUNT(DISTINCT id) AS unique_ids
FROM `fresh-yen-508710-a0.m5_raw.sales_train_validation`

UNION ALL

SELECT
  'sales_train_evaluation',
  COUNT(*),
  COUNTIF(id IS NULL),
  COUNT(DISTINCT id)
FROM `fresh-yen-508710-a0.m5_raw.sales_train_evaluation`;


-- 3. Sell Price Validation

SELECT
  COUNT(*) AS total_rows,
  COUNTIF(sell_price IS NULL) AS null_prices,
  COUNTIF(sell_price <= 0) AS invalid_prices
FROM `fresh-yen-508710-a0.m5_raw.sell_prices`;