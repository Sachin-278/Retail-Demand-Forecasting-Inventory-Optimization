import streamlit as st
from google.cloud import bigquery
import pandas as pd


st.set_page_config(
    page_title="Retail Demand Forecasting",
    page_icon="📦",
    layout="wide",
)


PROJECT_ID = "fresh-yen-508710-a0-509416"
FORECAST_TABLE = f"{PROJECT_ID}.dbt_dev_sachin.forecasts"


@st.cache_data
def load_forecast_data():
    """Load the latest LightGBM forecast rows from BigQuery."""

    client = bigquery.Client(project=PROJECT_ID)

    query = f"""
        SELECT
            item_id,
            store_id,
            state_id,
            dept_id,
            date,
            forecast_quantity,
            forecast_lower,
            forecast_upper,
            model_name,
            actual_quantity,
            generated_at
        FROM `{FORECAST_TABLE}`
        WHERE model_name = 'lightgbm_global'
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY item_id, store_id, date, model_name
            ORDER BY generated_at DESC
        ) = 1
        ORDER BY date
    """

    return client.query(query).to_dataframe()


@st.cache_data
def load_historical_data():
    """Load historical LightGBM holdout rows containing actual demand."""

    client = bigquery.Client(project=PROJECT_ID)

    query = f"""
        SELECT
            item_id,
            store_id,
            state_id,
            dept_id,
            date,
            forecast_quantity,
            forecast_lower,
            forecast_upper,
            model_name,
            actual_quantity,
            generated_at
        FROM `{FORECAST_TABLE}`
        WHERE model_name = 'lightgbm_global_holdout'
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY item_id, store_id, date, model_name
            ORDER BY generated_at DESC
        ) = 1
        ORDER BY date
    """

    return client.query(query).to_dataframe()


# ---------------------------------------------------------
# Load BigQuery data
# ---------------------------------------------------------

try:
    forecast_data = load_forecast_data()
    historical_data = load_historical_data()

    if forecast_data.empty:
        st.warning("No LightGBM forecast data was found.")
        st.stop()

    if historical_data.empty:
        st.warning("No historical LightGBM data was found.")
        st.stop()

except Exception as e:
    st.error("Unable to connect to the BigQuery forecasts table.")
    st.exception(e)
    st.stop()


# ---------------------------------------------------------
# Dashboard title
# ---------------------------------------------------------

st.title("📦 Retail Demand Forecasting & Inventory Optimization")

st.caption("Week 4 — Interactive Demand Forecast Dashboard")

st.markdown(
    """
    Use the filters in the sidebar to select a store, department, and item.
    The dashboard displays historical demand and future LightGBM forecasts
    from BigQuery.
    """
)


# ---------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------

st.sidebar.header("Dashboard Filters")

stores = sorted(
    forecast_data["store_id"].dropna().unique()
)

store = st.sidebar.selectbox(
    "Select Store",
    stores
)


store_forecast = forecast_data[
    forecast_data["store_id"] == store
]

store_historical = historical_data[
    historical_data["store_id"] == store
]


departments = sorted(
    store_forecast["dept_id"].dropna().unique()
)

category = st.sidebar.selectbox(
    "Select Category / Department",
    departments
)


department_forecast = store_forecast[
    store_forecast["dept_id"] == category
]

department_historical = store_historical[
    store_historical["dept_id"] == category
]


items = sorted(
    department_forecast["item_id"].dropna().unique()
)

item = st.sidebar.selectbox(
    "Select Item",
    items
)


# ---------------------------------------------------------
# Filter selected item
# ---------------------------------------------------------

selected_forecast = department_forecast[
    department_forecast["item_id"] == item
].copy()

selected_historical = department_historical[
    department_historical["item_id"] == item
].copy()


selected_forecast["date"] = pd.to_datetime(
    selected_forecast["date"]
)

selected_historical["date"] = pd.to_datetime(
    selected_historical["date"]
)


# ---------------------------------------------------------
# KPI section
# ---------------------------------------------------------

st.subheader("Demand Overview")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Selected Store",
        store
    )

with col2:
    st.metric(
        "Selected Department",
        category
    )

with col3:
    st.metric(
        "Selected Item",
        item
    )


# ---------------------------------------------------------
# Data status
# ---------------------------------------------------------

st.subheader("Forecast Status")

st.success(
    f"Loaded {len(forecast_data):,} future LightGBM forecast rows "
    f"and {len(historical_data):,} historical validation rows from BigQuery."
)


# ---------------------------------------------------------
# Historical + Forecast chart
# ---------------------------------------------------------

st.subheader("Historical Demand vs Forecast")

historical_chart = selected_historical[
    [
        "date",
        "actual_quantity"
    ]
].copy()

historical_chart = historical_chart.rename(
    columns={
        "actual_quantity": "Historical Actual"
    }
)

forecast_chart = selected_forecast[
    [
        "date",
        "forecast_quantity"
    ]
].copy()

forecast_chart = forecast_chart.rename(
    columns={
        "forecast_quantity": "Forecast"
    }
)


combined_chart = pd.concat(
    [
        historical_chart.set_index("date"),
        forecast_chart.set_index("date")
    ],
    axis=0
).sort_index()


st.line_chart(
    combined_chart,
    use_container_width=True
)


# ---------------------------------------------------------
# Forecast table
# ---------------------------------------------------------

st.subheader("Forecast Data")

display_forecast = selected_forecast[
    [
        "date",
        "forecast_quantity",
        "forecast_lower",
        "forecast_upper",
        "model_name",
    ]
].copy()

display_forecast["date"] = display_forecast[
    "date"
].dt.date


st.dataframe(
    display_forecast,
    use_container_width=True
)


# ---------------------------------------------------------
# Price What-If Scenario
# ---------------------------------------------------------

st.subheader("Price What-If Scenario")

st.info(
    "Price-change simulation will be added during Days 5–6 "
    "using the LightGBM model."
)