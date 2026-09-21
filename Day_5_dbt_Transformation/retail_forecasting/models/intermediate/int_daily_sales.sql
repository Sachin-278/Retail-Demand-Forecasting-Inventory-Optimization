{{ config(materialized='table') }}

SELECT
    s.item_id,
    s.dept_id,
    s.cat_id,
    s.store_id,
    s.state_id,
    c.date,
    c.wm_yr_wk,
    s.sales_quantity
FROM {{ ref('stg_sales_long') }} AS s
LEFT JOIN {{ ref('stg_calendar') }} AS c
    ON s.sales_day = c.d
WHERE c.date IS NOT NULL
