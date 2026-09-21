{{ config(materialized='table') }}

-- Clean, denormalized daily dataset for the forecasting layer.
-- This joins sales, calendar attributes, and price without creating
-- a model-specific forecast yet.

SELECT
    d.item_id,
    d.dept_id,
    d.cat_id,
    d.store_id,
    d.state_id,
    d.date,
    d.wm_yr_wk,
    d.sales_quantity,
    p.sell_price,
    c.weekday,
    c.wday,
    c.month,
    c.year,
    c.event_name_1,
    c.event_type_1,
    c.event_name_2,
    c.event_type_2,
    c.snap_CA,
    c.snap_TX,
    c.snap_WI
FROM {{ ref('int_daily_sales') }} AS d
LEFT JOIN {{ ref('stg_sell_prices') }} AS p
    ON d.store_id = p.store_id
   AND d.item_id = p.item_id
   AND d.wm_yr_wk = p.wm_yr_wk
LEFT JOIN {{ ref('stg_calendar') }} AS c
    ON d.wm_yr_wk = c.wm_yr_wk
   AND d.date = c.date
