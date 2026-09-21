{{ config(materialized='table') }}

SELECT
    item_id,
    dept_id,
    cat_id,
    store_id,
    state_id,
    DATE_TRUNC(date, WEEK(MONDAY)) AS week_start,
    SUM(sales_quantity) AS weekly_sales
FROM {{ ref('int_daily_sales') }}
GROUP BY
    item_id,
    dept_id,
    cat_id,
    store_id,
    state_id,
    week_start
