### Day 1 Validation Results

Hi team, here are the results from the basic validation checks on the `m5_raw` dataset:

**1. Table Check**
I ran the query to verify the tables, and all 5 required tables are present in the dataset.

**2. Columns and Data Types**
I checked the schema using INFORMATION_SCHEMA.COLUMNS. All data types (like INT64 for IDs and DATE for the calendar) look correct and match what we expect for the project.

**3. Row Counts**
Here is the row count for each table using the __TABLES__ meta-table:
* sell_prices: 6,841,121
* sample_submission: 60,980
* sales_train_validation: 30,490
* sales_train_evaluation: 30,490
* Calendar: 1,969

**4. Null Values**
I checked the essential columns (like id, item_id, store_id, and dates) across all the tables. Everything looks clean—the queries returned 0 missing values/nulls in the core columns.