{{ config(materialized='view') }}

SELECT
    store_id,
    item_id,
    wm_yr_wk,
    SAFE_CAST(sell_price AS FLOAT64) AS sell_price
FROM {{ source('m5_raw', 'sell_prices') }}
WHERE sell_price IS NOT NULL
  AND sell_price > 0
