# check Calender table columns,datatype
SELECT column_name, data_type
FROM `fresh-yen-508710-a0.m5_raw.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'Calendar';


# check Sales Train Validation table columns,datatype
SELECT column_name, data_type
FROM `fresh-yen-508710-a0.m5_raw.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'sales_train_validation';

# check Sales Train Evaluation table columns,datatype
SELECT column_name, data_type
FROM `fresh-yen-508710-a0.m5_raw.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'sales_train_evaluation';

# check Sell Prices table columns,datatype
SELECT column_name, data_type
FROM `fresh-yen-508710-a0.m5_raw.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'sell_prices';

# check Sample Submission table columns,datatype
SELECT column_name, data_type
FROM `fresh-yen-508710-a0.m5_raw.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'sample_submission';
