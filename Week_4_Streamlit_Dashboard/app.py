import streamlit as st
from google.cloud import bigquery
import pandas as pd
import sys
from pathlib import Path

# ---------------------------------------------------------
# Import Week 3 forecasting functions
# ---------------------------------------------------------

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1]
        / "Week_3_Time_Series_Forecasting"
    )
)

from forecast import train_lightgbm, forecast_lightgbm


# ---------------------------------------------------------
# Streamlit configuration
# ---------------------------------------------------------

st.set_page_config(
    page_title="Retail Demand Forecasting",
    page_icon="📦",
    layout="wide",
)


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

PROJECT_ID = "fresh-yen-508710-a0-509416"

FORECAST_TABLE = (
    f"{PROJECT_ID}.dbt_dev_sachin.forecasts"
)

INPUT_TABLE = (
    f"{PROJECT_ID}.dbt_dev_sachin.forecasting_input"
)

CALENDAR_TABLE = (
    f"{PROJECT_ID}.m5_raw.Calendar"
)

PRICE_TABLE = (
    f"{PROJECT_ID}.m5_raw.sell_prices"
)


# ---------------------------------------------------------
# Load forecast data
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# Load historical forecast / holdout data
# ---------------------------------------------------------

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
# Load training data for selected item/store
# ---------------------------------------------------------

@st.cache_data
def load_training_data(item_id, store_id):
    """Load historical sales and price data for LightGBM training."""

    client = bigquery.Client(project=PROJECT_ID)

    query = f"""
        SELECT
            item_id,
            store_id,
            state_id,
            dept_id,
            date,
            sales_quantity,
            sell_price,
            event_name_1,
            event_name_2,
            snap_CA,
            snap_TX,
            snap_WI
        FROM `{INPUT_TABLE}`
        WHERE item_id = @item_id
          AND store_id = @store_id
        ORDER BY date
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter(
                "item_id",
                "STRING",
                item_id
            ),
            bigquery.ScalarQueryParameter(
                "store_id",
                "STRING",
                store_id
            ),
        ]
    )

    data = client.query(
        query,
        job_config=job_config
    ).to_dataframe()

    return data


# ---------------------------------------------------------
# Build LightGBM model for selected item/store
# ---------------------------------------------------------

@st.cache_resource
def build_scenario_model(item_id, store_id):
    """Train the existing Week 3 LightGBM model for one item/store."""

    training_data = load_training_data(
        item_id,
        store_id
    )

    if training_data.empty:
        return None

    model = train_lightgbm(training_data)

    return model


# ---------------------------------------------------------
# Load future input data
# ---------------------------------------------------------

@st.cache_data
def load_future_covariates(
    item_id,
    store_id,
    start_date,
    end_date
):
    """
    Load future calendar and price inputs required by LightGBM.
    """

    client = bigquery.Client(project=PROJECT_ID)

    query = f"""
        WITH calendar AS (
            SELECT
                COALESCE(
                    SAFE_CAST(date AS DATE),
                    SAFE.PARSE_DATE(
                        '%m/%d/%y',
                        CAST(date AS STRING)
                    )
                ) AS forecast_date,

                wm_yr_wk,
                event_name_1,
                event_name_2,
                snap_CA,
                snap_TX,
                snap_WI

            FROM `{CALENDAR_TABLE}`
        ),

        series AS (
            SELECT
                item_id,
                store_id,
                ANY_VALUE(state_id) AS state_id,
                ANY_VALUE(dept_id) AS dept_id

            FROM `{INPUT_TABLE}`

            WHERE item_id = @item_id
              AND store_id = @store_id

            GROUP BY
                item_id,
                store_id
        )

        SELECT
            series.item_id,
            series.store_id,
            series.state_id,
            series.dept_id,

            calendar.forecast_date AS date,

            calendar.event_name_1,
            calendar.event_name_2,

            calendar.snap_CA,
            calendar.snap_TX,
            calendar.snap_WI,

            SAFE_CAST(
                prices.sell_price AS FLOAT64
            ) AS sell_price

        FROM calendar

        CROSS JOIN series

        LEFT JOIN `{PRICE_TABLE}` AS prices

            ON prices.item_id = series.item_id
            AND prices.store_id = series.store_id
            AND prices.wm_yr_wk = calendar.wm_yr_wk

        WHERE calendar.forecast_date >= @start_date
          AND calendar.forecast_date <= @end_date

        ORDER BY date
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter(
                "item_id",
                "STRING",
                item_id
            ),
            bigquery.ScalarQueryParameter(
                "store_id",
                "STRING",
                store_id
            ),
            bigquery.ScalarQueryParameter(
                "start_date",
                "DATE",
                start_date
            ),
            bigquery.ScalarQueryParameter(
                "end_date",
                "DATE",
                end_date
            ),
        ]
    )

    return client.query(
        query,
        job_config=job_config
    ).to_dataframe()


# ---------------------------------------------------------
# Run price what-if scenario
# ---------------------------------------------------------

def run_price_scenario(
    item_id,
    store_id,
    price_change_pct,
    forecast_start,
    forecast_end
):
    """
    Run LightGBM twice:

    1. Original real price
    2. Modified scenario price

    Returns both forecasts.
    """

    training_data = load_training_data(
        item_id,
        store_id
    )

    if training_data.empty:
        return None, None, None

    model = build_scenario_model(
        item_id,
        store_id
    )

    if model is None:
        return None, None, None

    future_data = load_future_covariates(
        item_id,
        store_id,
        forecast_start,
        forecast_end
    )

    if future_data.empty:
        return None, None, None

    future_data["date"] = pd.to_datetime(
        future_data["date"]
    )

    # -----------------------------------------------------
    # Original real price
    # -----------------------------------------------------

    original_data = future_data.copy()

    # -----------------------------------------------------
    # Scenario price
    # -----------------------------------------------------

    scenario_data = future_data.copy()

    scenario_data["sell_price"] = (
        scenario_data["sell_price"]
        * (1 + price_change_pct / 100)
    )

    # -----------------------------------------------------
    # Run original forecast
    # -----------------------------------------------------

    original_forecast = forecast_lightgbm(
        model,
        training_data,
        horizon=len(original_data),
        future_features=original_data,
    )

    # -----------------------------------------------------
    # Run scenario forecast
    # -----------------------------------------------------

    scenario_forecast = forecast_lightgbm(
        model,
        training_data,
        horizon=len(scenario_data),
        future_features=scenario_data,
    )

    return (
        original_forecast,
        scenario_forecast,
        future_data
    )


# ---------------------------------------------------------
# Load BigQuery data
# ---------------------------------------------------------

try:

    forecast_data = load_forecast_data()

    historical_data = load_historical_data()

    if forecast_data.empty:
        st.warning(
            "No LightGBM forecast data was found."
        )
        st.stop()

    if historical_data.empty:
        st.warning(
            "No historical LightGBM data was found."
        )
        st.stop()

except Exception as e:

    st.error(
        "Unable to connect to the BigQuery forecasts table."
    )

    st.exception(e)

    st.stop()


# ---------------------------------------------------------
# Dashboard title
# ---------------------------------------------------------

st.title(
    "📦 Retail Demand Forecasting & Inventory Optimization"
)

st.caption(
    "Week 4 — Interactive Demand Forecast Dashboard"
)

st.markdown(
    """
    Use the filters in the sidebar to select a store,
    department, and item. The dashboard displays historical
    demand and future LightGBM forecasts from BigQuery.
    """
)


# ---------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------

st.sidebar.header(
    "Dashboard Filters"
)


stores = sorted(
    forecast_data["store_id"]
    .dropna()
    .unique()
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
    store_forecast["dept_id"]
    .dropna()
    .unique()
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
    department_forecast["item_id"]
    .dropna()
    .unique()
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

st.subheader(
    "Demand Overview"
)


forecast_days = selected_forecast[
    "date"
].nunique()


total_forecast_demand = selected_forecast[
    "forecast_quantity"
].sum()


average_daily_demand = selected_forecast[
    "forecast_quantity"
].mean()


peak_forecast_demand = selected_forecast[
    "forecast_quantity"
].max()


col1, col2, col3, col4 = st.columns(4)


with col1:

    st.metric(
        "Forecast Horizon",
        f"{forecast_days} days"
    )


with col2:

    st.metric(
        "Total Forecast Demand",
        f"{total_forecast_demand:.1f}"
    )


with col3:

    st.metric(
        "Average Daily Demand",
        f"{average_daily_demand:.2f}"
    )


with col4:

    st.metric(
        "Peak Daily Demand",
        f"{peak_forecast_demand:.2f}"
    )


# ---------------------------------------------------------
# Forecast status
# ---------------------------------------------------------

st.subheader(
    "Forecast Status"
)


forecast_start = selected_forecast[
    "date"
].min()


forecast_end = selected_forecast[
    "date"
].max()


forecast_days = selected_forecast[
    "date"
].nunique()


st.success(
    f"LightGBM forecast loaded for {forecast_days} days "
    f"from {forecast_start.date()} to "
    f"{forecast_end.date()}."
)


status_col1, status_col2, status_col3 = st.columns(3)


with status_col1:

    st.metric(
        "Forecast Start",
        forecast_start.strftime("%d %b %Y")
    )


with status_col2:

    st.metric(
        "Forecast End",
        forecast_end.strftime("%d %b %Y")
    )


with status_col3:

    st.metric(
        "Forecast Days",
        forecast_days
    )


# ---------------------------------------------------------
# Historical + Forecast chart
# ---------------------------------------------------------

st.subheader(
    "Historical Demand vs Forecast"
)


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
# Forecast Summary
# ---------------------------------------------------------

st.subheader(
    "Forecast Summary"
)


summary_col1, summary_col2 = st.columns(2)


with summary_col1:

    st.write(
        "**Selected Store:**",
        store
    )

    st.write(
        "**Selected Department:**",
        category
    )

    st.write(
        "**Selected Item:**",
        item
    )


with summary_col2:

    st.write(
        "**Forecast Period:**",
        f"{forecast_start.strftime('%d %b %Y')} "
        f"to {forecast_end.strftime('%d %b %Y')}"
    )

    st.write(
        "**Total Expected Demand:**",
        f"{total_forecast_demand:.1f} units"
    )


# ---------------------------------------------------------
# Forecast table
# ---------------------------------------------------------

st.subheader(
    "Forecast Data"
)


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

st.subheader(
    "💰 Price What-If Scenario"
)


st.write(
    """
    Simulate a price change and see how the LightGBM model
    projects demand under the new price.
    """
)


price_change_pct = st.slider(
    "Price change (%)",
    min_value=-30,
    max_value=30,
    value=0,
    step=5,
    help=(
        "Negative values decrease the price. "
        "Positive values increase the price."
    )
)


# ---------------------------------------------------------
# Show current price
# ---------------------------------------------------------

try:

    future_price_data = load_future_covariates(
        item,
        store,
        forecast_start.date(),
        forecast_end.date()
    )

    if not future_price_data.empty:

        current_price = future_price_data[
            "sell_price"
        ].dropna().iloc[0]

        scenario_price = (
            current_price
            * (1 + price_change_pct / 100)
        )

        price_col1, price_col2, price_col3 = st.columns(3)

        with price_col1:

            st.metric(
                "Current Price",
                f"{current_price:.2f}"
            )

        with price_col2:

            st.metric(
                "Price Change",
                f"{price_change_pct:+.0f}%"
            )

        with price_col3:

            st.metric(
                "Scenario Price",
                f"{scenario_price:.2f}"
            )

    else:

        st.warning(
            "No future price data was found for the selected item."
        )

except Exception as e:

    st.warning(
        "Unable to load price information."
    )

    st.exception(e)


# ---------------------------------------------------------
# Run scenario
# ---------------------------------------------------------

if st.button(
    "Run Price What-If Scenario",
    type="primary"
):

    with st.spinner(
        "Training LightGBM and calculating scenario demand..."
    ):

        try:

            (
                original_forecast,
                scenario_forecast,
                future_price_data
            ) = run_price_scenario(
                item_id=item,
                store_id=store,
                price_change_pct=price_change_pct,
                forecast_start=forecast_start.date(),
                forecast_end=forecast_end.date()
            )


            if (
                original_forecast is None
                or scenario_forecast is None
            ):

                st.error(
                    "Unable to generate the price scenario."
                )

            else:

                # -----------------------------------------
                # Convert predictions to dataframes
                # -----------------------------------------

                original_result = original_forecast[
                    [
                        "date",
                        "forecast_quantity"
                    ]
                ].copy()

                original_result = original_result.rename(
                    columns={
                        "forecast_quantity":
                        "Original Forecast"
                    }
                )


                scenario_result = scenario_forecast[
                    [
                        "date",
                        "forecast_quantity"
                    ]
                ].copy()

                scenario_result = scenario_result.rename(
                    columns={
                        "forecast_quantity":
                        "Scenario Forecast"
                    }
                )


                original_result["date"] = pd.to_datetime(
                    original_result["date"]
                )

                scenario_result["date"] = pd.to_datetime(
                    scenario_result["date"]
                )


                comparison = original_result.merge(
                    scenario_result,
                    on="date"
                )


                comparison[
                    "Demand Change"
                ] = (
                    comparison["Scenario Forecast"]
                    - comparison["Original Forecast"]
                )


                # -----------------------------------------
                # Scenario KPIs
                # -----------------------------------------

                original_total = (
                    comparison[
                        "Original Forecast"
                    ].sum()
                )


                scenario_total = (
                    comparison[
                        "Scenario Forecast"
                    ].sum()
                )


                demand_change = (
                    scenario_total
                    - original_total
                )


                if original_total != 0:

                    demand_change_pct = (
                        demand_change
                        / original_total
                        * 100
                    )

                else:

                    demand_change_pct = 0


                st.success(
                    "Price scenario calculated successfully."
                )


                st.subheader(
                    "Scenario Results"
                )


                result_col1, result_col2, result_col3 = st.columns(3)


                with result_col1:

                    st.metric(
                        "Original Demand",
                        f"{original_total:.2f} units"
                    )


                with result_col2:

                    st.metric(
                        "Scenario Demand",
                        f"{scenario_total:.2f} units"
                    )


                with result_col3:

                    st.metric(
                        "Demand Change",
                        f"{demand_change:+.2f} "
                        f"({demand_change_pct:+.2f}%)"
                    )


                # -----------------------------------------
                # Scenario chart
                # -----------------------------------------

                st.subheader(
                    "Original vs Price Scenario Demand"
                )


                scenario_chart = comparison[
                    [
                        "date",
                        "Original Forecast",
                        "Scenario Forecast"
                    ]
                ].set_index("date")


                st.line_chart(
                    scenario_chart,
                    use_container_width=True
                )


                # -----------------------------------------
                # Scenario table
                # -----------------------------------------

                st.subheader(
                    "Price Scenario Forecast Data"
                )


                display_scenario = comparison.copy()


                display_scenario["date"] = (
                    display_scenario["date"].dt.date
                )


                st.dataframe(
                    display_scenario,
                    use_container_width=True
                )


        except Exception as e:

            st.error(
                "The price scenario could not be calculated."
            )

            st.exception(e)