-- 1. Check for NULLs in the Calendar table
SELECT 
  COUNTIF(date IS NULL) AS missing_dates,
  COUNTIF(wm_yr_wk IS NULL) AS missing_weeks,
  COUNTIF(d IS NULL) AS missing_d_values
FROM `fresh-yen-508710-a0.m5_raw.Calendar`;

-- 2. Check for NULLs in the Sell Prices table
SELECT 
  COUNTIF(store_id IS NULL) AS missing_stores,
  COUNTIF(item_id IS NULL) AS missing_items,
  COUNTIF(wm_yr_wk IS NULL) AS missing_weeks,
  COUNTIF(sell_price IS NULL) AS missing_prices
FROM `fresh-yen-508710-a0.m5_raw.sell_prices`;

 -- 3. Check for NULLs in essential Sales Validation columns
SELECT 
  COUNTIF(id IS NULL) AS missing_ids,
  COUNTIF(item_id IS NULL) AS missing_items,
  COUNTIF(store_id IS NULL) AS missing_stores
FROM `fresh-yen-508710-a0.m5_raw.sales_train_validation`;


-- 4. Check for NULLs in essential Sales Evaluation columns
SELECT 
  COUNTIF(id IS NULL) AS missing_ids,
  COUNTIF(item_id IS NULL) AS missing_items,
  COUNTIF(store_id IS NULL) AS missing_stores
FROM `fresh-yen-508710-a0.m5_raw.sales_train_evaluation`;

-- 5. Check for NULLs in the Sample Submission table
SELECT 
  COUNTIF(id IS NULL) AS missing_ids,
  COUNTIF(F1 IS NULL) AS missing_f1
FROM `fresh-yen-508710-a0.m5_raw.sample_submission`;