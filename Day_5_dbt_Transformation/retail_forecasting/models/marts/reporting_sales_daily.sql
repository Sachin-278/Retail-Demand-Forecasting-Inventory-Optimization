{{ config(materialized='view') }}

-- Dashboard-ready daily sales totals by store and product hierarchy.
SELECT
    date,
    state_id,
    store_id,
    cat_id,
    dept_id,
    SUM(sales_quantity) AS total_sales_quantity,
    COUNT(DISTINCT item_id) AS item_count,
    AVG(sell_price) AS average_sell_price,
    COUNTIF(event_name_1 IS NOT NULL OR event_name_2 IS NOT NULL) AS event_item_count
FROM {{ ref('forecasting_input') }}
GROUP BY
    date,
    state_id,
    store_id,
    cat_id,
    dept_id