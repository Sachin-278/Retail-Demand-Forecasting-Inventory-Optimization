# checking row count 

SELECT 
  table_id AS table_name, 
  row_count
FROM `fresh-yen-508710-a0.m5_raw.__TABLES__`
ORDER BY row_count DESC;