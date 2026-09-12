# Retail Demand Forecasting & Inventory Optimization

> **Project documentation** for a data platform that forecasts retail demand and supports inventory, pricing, and procurement decisions.

## Document Overview

| Field | Description |
| --- | --- |
| Project | Retail Demand Forecasting & Inventory Optimization |
| Primary dataset | Walmart M5 Forecasting dataset |
| Main objective | Predict future demand at multiple retail hierarchy levels |
| Decision users | Procurement teams, inventory managers, and store managers |
| Planned delivery | Four-week implementation roadmap |
| Core technologies | Cloud warehouse, dbt, Prophet, LightGBM, and Streamlit |

## Executive Summary

Retail supply chains must balance two costly outcomes: stockouts, which cause lost sales and reduced customer trust, and overstocking, which ties up capital and warehouse capacity. This project documents a proactive forecasting system that predicts demand days or weeks ahead so procurement and inventory decisions can be based on data rather than reactive reorder rules.

The system is designed as an analytics engineering and time-series forecasting project. It combines a cloud data warehouse, dbt-managed transformations, two complementary forecasting approaches, and an interactive dashboard for operational decision support.

## Contents

- [1. Business Problem](#1-business-problem)
- [2. Data Source](#2-data-source)
- [3. Solution Architecture](#3-solution-architecture)
- [4. Forecasting Strategy](#4-forecasting-strategy)
- [5. Implementation Roadmap](#5-implementation-roadmap)
- [6. Dashboard Requirements](#6-dashboard-requirements)
- [7. Comparison With Previous Projects](#7-comparison-with-previous-projects)
- [8. Project Outcome](#8-project-outcome)

## 1. Business Problem

Retail supply chains face a constant balancing act: stockouts (running out of a popular item, losing sales and customer trust) versus overstocking (tying up cash and warehouse space in inventory that isn't selling). Traditional retail purchasing is often reactive - reorder when stock gets low, based on gut feel or simple moving averages. This project replaces that with proactive forecasting: predicting demand days/weeks ahead so procurement decisions are made from data, not instinct.

This is a time-series forecasting problem - fundamentally different from Projects 1 and 2. Project 1 predicted a category (churn: yes/no) and a value (LTV) per customer, independent of time. Project 3 predicts a sequence of future values (daily/weekly demand) where the order and timing of past observations directly shapes the prediction - seasonality, trends, holidays, and promotions all matter in ways they didn't in the other two projects.

## 2. Data Source

M5 is a well-known forecasting competition dataset from Walmart, via the M-competitions series and hosted on Kaggle. It contains:

- **Hierarchical structure:** individual items -> departments -> product categories -> stores -> states. This hierarchy matters because forecasting must work at multiple levels, from a single SKU in one store to aggregated totals across all stores. The levels should ideally be coherent, so department totals roughly match the sum of their item-level forecasts.
- **Several years of daily sales history:** enough data to capture yearly seasonality, such as holiday spikes, in addition to weekly patterns.
- **Calendar events:** holidays and special events that shift demand.
- **Pricing data:** price changes that affect demand and support the "what-if" scenarios planned for Week 4.

This is a notoriously large and complex dataset, with tens of millions of rows once expanded. That scale is part of why the tech stack uses a cloud data warehouse rather than relying only on local Pandas processing.

## 3. Solution Architecture

```text
[Raw M5 Data] -> [BigQuery/Snowflake] -> [dbt transformations] -> [Prophet/LightGBM] -> [Warehouse] -> [Streamlit Dashboard]
	(ingest)          (storage)              (clean/aggregate)         (forecast)         (store)         (serve)
```

| Tool | Role | Why it's used here |
| --- | --- | --- |
| BigQuery / Snowflake | Cloud data warehouse | Handles the scale of M5 data efficiently with SQL-based querying and separates storage from compute - standard for modern data teams instead of a single PostgreSQL instance. |
| dbt (Data Build Tool) | Data transformation | Defines transformations as SQL with version control, testing, and documentation rather than ad-hoc scripts. This is the industry-standard "T" in ELT (Extract, Load, Transform). |
| Facebook Prophet | Time-series forecasting | Designed for business time series with strong seasonal patterns and holiday effects. It handles missing data and trend shifts gracefully with minimal tuning. |
| ARIMA | Classical time-series model | A statistical approach that is useful for series with clear autocorrelation structure and as a comparison baseline. |
| LightGBM | Gradient boosting (tabular ML) | Used for granular SKU forecasting with irregular or sparse demand, where price, promotions, day-of-week, lag features, and rolling statistics add predictive power. |
| Streamlit | Interactive web app | Builds a Python-only interactive dashboard quickly for inventory managers exploring forecasts by store or category. |
| Tableau | BI/visualization alternative | A more polished enterprise BI option when the audience is broader or less technical than an internal operations team. |

### Why dbt here, when Project 1 didn't have it?

Project 1's transformations were simple enough to do inline in Pandas. Project 3 deals with a much larger, hierarchical dataset where transformations (daily -> weekly/monthly aggregation and building clean marts for different consumers) benefit from being version-controlled, testable, and documented as part of the data pipeline. This is exactly what dbt is built for, and it is a common modern data-stack pattern.

## 4. Forecasting Strategy

### Why two different forecasting approaches (Prophet vs. LightGBM)?

This reflects a real forecasting trade-off:

- **Prophet** is well suited to high-volume aggregate series, such as total department sales, where clean seasonal and trend decomposition is meaningful and there are fewer exogenous features to leverage.
- **LightGBM** is better for granular item-level forecasting, where thousands of SKU-store combinations may have sparse or intermittent sales and extra features such as price, promotions, lag values, and rolling averages add predictive power.

## 5. Implementation Roadmap

### Week 1: Data Architecture & ETL

#### Days 1-3 - Setup warehouse + extraction

Provision BigQuery or Snowflake and write scripts to load the raw M5 CSVs (sales, calendar, and pricing tables) into the warehouse. This is the "E" and "L" in ELT: get raw data into the warehouse before transforming it rather than transforming it on the way in. This pattern scales better and keeps a full raw copy for reprocessing if transformation logic changes later.

#### Days 4-7 - Data quality checks & formatting

- Parse dates correctly so the calendar table aligns with the sales table on date keys.
- Check for negative or missing sales values, duplicate rows, and inconsistent SKU IDs across tables.
- Standardize pricing formats.

This step matters more here than in Project 1 because M5's hierarchical, multi-table structure creates more opportunities for join errors and mismatched keys that could silently corrupt downstream forecasts.

### Week 2: Data Transformation with dbt

#### Days 1-3 - Configure dbt

Connect dbt to the warehouse using a `profiles.yml` connection config and set up the project structure:

- `models/`
- `sources.yml`, defining the raw tables dbt reads from
- Staging models for light cleaning, renaming, and type-casting on top of raw tables

#### Days 4-6 - Build aggregation models & data marts

Write SQL-based dbt models that:

- Aggregate daily sales into weekly and monthly views, useful for higher-level trend analysis and for Prophet, which works well on less noisy aggregated series.
- Build clean data marts - purpose-built, denormalized tables for specific downstream uses. For example, a `forecasting_input` mart with sales, calendar, and price joined and ready to feed into models, separate from a reporting mart for dashboards.

dbt models are chained: a staging model feeds into an intermediate model, which feeds into a final mart. dbt tracks these dependencies automatically and can run them in the correct order.

#### Day 7 - Document lineage

dbt auto-generates a data lineage graph (a DAG showing how each table is derived from raw sources through every transformation step) plus documentation for each model and column. When a number looks wrong, lineage documentation makes it possible to trace exactly where it came from.

### Week 3: Time-Series Forecasting

#### Days 1-3 - Facebook Prophet for high-volume products

Prophet decomposes a time series into trend, seasonality (weekly/yearly), and holiday effects using an additive model. For high-volume products or departments, fit a Prophet model per series (or per aggregated group) and explicitly feed in M5 calendar events, such as Thanksgiving, Christmas, and sporting events, as holiday regressors.

#### Days 4-6 - LightGBM for granular, item-level forecasting

For each item-store-day, reframe forecasting as a supervised regression problem and construct features such as:

- Lag features: sales 7 days ago and 28 days ago
- Rolling averages and standard deviations
- Day-of-week, month, and holiday flags
- Price and promotion indicators

LightGBM then predicts next-period demand directly. This approach scales much better across thousands of SKUs than fitting a separate Prophet model per item and naturally incorporates price and promotion effects as regular features.

#### Day 7 - Store forecast outputs

Write predicted and actual demand back into the warehouse in a new `forecasts` table. This closes the loop: Week 4's dashboard can query forecasts directly from the warehouse rather than recomputing them live, and forecast accuracy can be tracked over time.

### Week 4: Interactive Dashboard & Reporting

#### Days 1-4 - Streamlit app

Build a web app where an inventory manager can:

- Select a store and category or item.
- View a 30-day demand forecast chart with predicted and historical actuals.
- See confidence intervals alongside the point forecast, since inventory decisions benefit from knowing the range of plausible demand.

#### Days 5-6 - "What-if" scenario inputs

Let users simulate scenarios such as, "What if we drop the price by 10%?" and see the projected impact on demand. This requires the underlying model, typically LightGBM because it has price as an explicit feature, to support counterfactual inference: take a real input row, modify the price feature, and rerun the prediction.

This turns the tool from a passive forecast viewer into a decision-support tool for pricing and promotion planning.

#### Day 7 - Final touches

Complete code review, access control, and handover documentation. Since the system touches sales and pricing data, access should be restricted appropriately; for example, store managers should see only their own store.

## 6. Dashboard Requirements

The dashboard is intended to be an operational tool rather than a static report. It should allow an inventory manager to filter by store, category, or item; inspect historical demand and a 30-day forecast; review uncertainty; and test pricing scenarios before making a decision.

The required user workflow is:

1. Select a store and product category or item.
2. Review historical actual demand and the 30-day forecast.
3. Inspect confidence intervals or a plausible demand range.
4. Adjust a scenario input, such as a 10% price reduction.
5. Compare the baseline forecast with the counterfactual forecast.
6. Use the result to support replenishment, pricing, or promotion planning.

## 7. Comparison With Previous Projects

|  | Project 1 (Churn/LTV) | Project 2 (Fraud) | Project 3 (Demand Forecasting) |
| --- | --- | --- | --- |
| Data arrival | Static batch | Continuous stream | Static batch, but time-ordered |
| Core discipline | Data science / ML | Data engineering + ML | Analytics engineering + forecasting |
| Prediction type | Classification + regression | Anomaly scoring | Time-series forecasting |
| Key data challenge | Cleaning/encoding | Latency at scale | Hierarchical aggregation, seasonality |
| Storage | PostgreSQL | Cassandra (high write) | BigQuery/Snowflake (analytical) |
| Transformation approach | Ad-hoc Pandas | Spark micro-batches | dbt-managed SQL models |
| Dashboard purpose | Business insight (segments) | System/fraud monitoring | Operational decision-support (what-if) |
| Failure cost | Suboptimal marketing spend | Financial/regulatory loss | Stockouts or excess inventory cost |

This project is the most analytics-engineering-flavored of the three: it combines the modern data stack (warehouse + dbt) with time-series-specific modeling and culminates in an interactive decision tool rather than just a report.

## 8. Project Outcome

At completion, the project should provide:

- A reliable raw-data ingestion process for the M5 dataset.
- Tested and documented dbt transformations.
- Aggregated and item-level forecasting inputs.
- Forecast outputs stored in the warehouse for reuse and monitoring.
- Forecast accuracy tracking over time.
- A Streamlit dashboard for store and product exploration.
- What-if analysis for price and promotion scenarios.
- Access controls and handover documentation suitable for operational use.

The intended result is a repeatable decision-support workflow that reduces the risk of stockouts and unnecessary overstock while making the assumptions behind each forecast traceable.
