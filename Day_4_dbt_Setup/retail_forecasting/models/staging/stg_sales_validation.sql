SELECT
    id,
    item_id,
    dept_id,
    cat_id,
    store_id,
    state_id,
    *
EXCEPT (
    id,
    item_id,
    dept_id,
    cat_id,
    store_id,
    state_id
)
FROM {{ source('m5_raw', 'sales_train_validation') }}
