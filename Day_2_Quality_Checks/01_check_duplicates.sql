--Check for duplicates to all individual tables in the m5_raw dataset
SELECT 
  date, 
  COUNT(*) as duplicate_count
FROM `fresh-yen-508710-a0.m5_raw.Calendar`
GROUP BY date
HAVING COUNT(*) > 1;

--Check sell_prices table for duplicates based on store_id, item_id, and wm_yr_wk
SELECT 
  store_id, 
  item_id, 
  wm_yr_wk, 
  COUNT(*) as duplicate_count
FROM `fresh-yen-508710-a0.m5_raw.sell_prices`
GROUP BY store_id, item_id, wm_yr_wk
HAVING COUNT(*) > 1;

--Check for duplicates in sales_train_validation, sales_train_evaluation, and sample_submission tables based on id
SELECT 
  id, 
  COUNT(*) as duplicate_count
FROM `fresh-yen-508710-a0.m5_raw.sales_train_validation`
GROUP BY id
HAVING COUNT(*) > 1;

--Check for duplicates in sales_train_evaluation table 
SELECT 
  id, 
  COUNT(*) as duplicate_count
FROM `fresh-yen-508710-a0.m5_raw.sales_train_evaluation`
GROUP BY id
HAVING COUNT(*) > 1;

--Check for duplicates in sample_submission table
SELECT 
  id, 
  COUNT(*) as duplicate_count
FROM `fresh-yen-508710-a0.m5_raw.sample_submission`
GROUP BY id
HAVING COUNT(*) > 1;