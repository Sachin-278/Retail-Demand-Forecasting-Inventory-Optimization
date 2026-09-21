{{ config(materialized='view') }}

SELECT *
FROM {{ source('m5_raw', 'sales_train_validation') }}
