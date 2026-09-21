
 -- Validation: Verify all 5 tables are present and contain data

-- 1. Check Calendar table
SELECT * FROM `fresh-yen-508710-a0.m5_raw.Calendar` LIMIT 5;

-- 2. Check Sales Train Validation table
SELECT * FROM `fresh-yen-508710-a0.m5_raw.sales_train_validation` LIMIT 5;

-- 3. Check Sales Train Evaluation table
SELECT * FROM `fresh-yen-508710-a0.m5_raw.sales_train_evaluation` LIMIT 5;

-- 4. Check Sell Prices table
SELECT * FROM `fresh-yen-508710-a0.m5_raw.sell_prices` LIMIT 5;

-- 5. Check Sample Submission table
SELECT * FROM `fresh-yen-508710-a0.m5_raw.sample_submission` LIMIT 5;

