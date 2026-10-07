\# Week 4 - Streamlit Demand Forecasting Dashboard



\## Overview



This Streamlit dashboard provides an interactive view of retail demand forecasts and inventory-related demand scenarios.



The dashboard connects to BigQuery to retrieve historical sales and forecast data and presents the results in an easy-to-understand format for inventory managers.



\## Features



\- Store and item selection

\- Historical demand visualization

\- 28-day demand forecast

\- Forecast KPIs

\- Predicted vs historical demand chart

\- Price what-if scenario analysis

\- Comparison of original and scenario demand

\- Demand change percentage

\- BigQuery integration



\## Forecast Information



The dashboard uses forecast results generated during Week 3.



Forecast data includes:



\- Item

\- Store

\- Department

\- Forecast date

\- Forecast quantity

\- Forecast lower bound

\- Forecast upper bound

\- Actual quantity

\- Model name



\## Price What-If Analysis



The dashboard allows users to simulate a price change and compare the expected demand with the original forecast.



For example, a user can increase or decrease the current product price and view the resulting demand change.



The scenario prediction uses the LightGBM forecasting model.



\## How to Run



From the project root:



```powershell

py -3.14 -m streamlit run .\\Week\_4\_Streamlit\_Dashboard\\app.py

