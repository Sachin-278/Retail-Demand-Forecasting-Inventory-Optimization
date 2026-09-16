# BigQuery RAW Layer

## Project

Retail-Demand-Forecasting

## Dataset

`m5_raw`

## RAW Tables

The M5 raw datasets have been loaded into the `m5_raw` dataset in BigQuery.

The following raw tables are available:

- `Calendar`
- `sales_train_validation`
- `sales_train_evaluation`
- `sell_prices`
- `sample_submission`

## Purpose of the RAW Layer

The RAW layer stores the original M5 datasets in BigQuery so that the data can be validated and used for further transformation.

No major business transformations are applied at this stage.

## Member 1 Work

The following Task 1 work was completed:

- Studied the M5 dataset structure and relationships.
- Set up the BigQuery project and `m5_raw` dataset.
- Created the required RAW tables.
- Loaded the M5 datasets into BigQuery.
- Performed initial data validation checks.
- Added validation SQL and dataset documentation to the repository.

## Member 2 Handover

The RAW layer is now available for independent validation by Member 2.

The validation includes:

- Table and schema checks
- Row count checks
- NULL/missing value checks
- Duplicate checks
- Date validation
- Sales validation
- Price validation
- Item/store/week/price relationship checks

## Next Step

After RAW layer validation is completed, the validated data will be handed over to Task 2 for dbt transformation.