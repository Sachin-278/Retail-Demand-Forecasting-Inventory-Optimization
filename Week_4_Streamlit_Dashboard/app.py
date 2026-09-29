import streamlit as st

st.set_page_config(
    page_title="Retail Demand Forecasting",
    page_icon="📦",
    layout="wide",
)

# -----------------------------
# Header
# -----------------------------
st.title("📦 Retail Demand Forecasting & Inventory Optimization")
st.caption("Week 4 — Interactive Demand Forecast Dashboard")

st.markdown(
    """
    Use the filters in the sidebar to select a store, category, and item.
    The dashboard will display historical demand and future demand forecasts.
    """
)

# -----------------------------
# Sidebar filters
# -----------------------------
st.sidebar.header("Dashboard Filters")

store = st.sidebar.selectbox(
    "Select Store",
    ["Select a store"],
)

category = st.sidebar.selectbox(
    "Select Category",
    ["Select a category"],
)

item = st.sidebar.selectbox(
    "Select Item",
    ["Select an item"],
)

# -----------------------------
# KPI section
# -----------------------------
st.subheader("Demand Overview")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Selected Store", store)

with col2:
    st.metric("Selected Category", category)

with col3:
    st.metric("Selected Item", item)

# -----------------------------
# Forecast section
# -----------------------------
st.subheader("Demand Forecast")

st.info(
    "Forecast data from the Week 3 BigQuery forecasts table "
    "will be connected here."
)

st.markdown("### Forecast Visualization")

st.write(
    "The forecast chart will display historical actual demand "
    "and future predicted demand."
)

# -----------------------------
# What-if section
# -----------------------------
st.subheader("Price What-If Scenario")

st.write(
    "A price-change scenario will be added here to estimate "
    "the potential demand impact."
)