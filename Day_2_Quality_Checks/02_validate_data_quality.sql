-- Check for invalid or unexpected state and category values

SELECT DISTINCT state_id, cat_id
FROM `fresh-yen-508710-a0.m5_raw.sales_train_validation`
WHERE state_id NOT IN ('CA', 'TX', 'WI')
   OR cat_id NOT IN ('FOODS', 'HOBBIES', 'HOUSEHOLD');

-- Check for missing or invalid dates

SELECT COUNT(*) AS invalid_date_count
FROM `fresh-yen-508710-a0.m5_raw.Calendar`
WHERE date IS NULL;

-- Check the date range

SELECT MIN(date) AS min_date, MAX(date) AS max_date
FROM `fresh-yen-508710-a0.m5_raw.Calendar`;

-- Check for negative sales values

SELECT COUNT(*) AS negative_sales_count
FROM `fresh-yen-508710-a0.m5_raw.sales_train_validation`
WHERE d_1 < 0
   OR d_2 < 0
   OR d_3 < 0;

--check for invalid sell_price values (negative or zero)

SELECT COUNT(*) as invalid_price_count
FROM `fresh-yen-508710-a0.m5_raw.sell_prices`
WHERE sell_price <= 0;

 -- Check for duplicate item, store, and week combinations

SELECT
  item_id,
  store_id,
  wm_yr_wk,
  COUNT(*) AS duplicate_count
FROM `fresh-yen-508710-a0.m5_raw.sell_prices`
GROUP BY item_id, store_id, wm_yr_wk
HAVING COUNT(*) > 1;