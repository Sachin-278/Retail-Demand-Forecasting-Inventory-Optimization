{{ config(materialized='table') }}

SELECT
    item_id,
    dept_id,
    cat_id,
    store_id,
    state_id,
    DATE_TRUNC(date, MONTH) AS month_start,
    SUM(sales_quantity) AS monthly_sales
FROM {{ ref('int_daily_sales') }}
GROUP BY
    item_id,
    dept_id,
    cat_id,
    store_id,
    state_id,
    month_start
