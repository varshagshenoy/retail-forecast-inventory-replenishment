# Project Overview

This project builds an end-to-end analytics pipeline for retail inventory optimization.

The objective is to improve product availability while controlling inventory holding costs across multiple stores and SKUs.

The solution integrates:

- Data cleaning and ETL pipeline

- Demand forecasting

- Inventory replenishment policy

- Business impact estimation

- Interactive dashboard for monitoring and decision support

The system operates at store–SKU granularity and generates forecasts and replenishment recommendations for the next 28 days.

# North Star Metric

The North Star metric for the project is Service Level (Fill Rate).

Fill Rate = True Demand / Units Sold

Fill rate measures the percentage of customer demand that is fulfilled from available inventory.

Improving fill rate indicates:

- better product availability

- reduced lost sales

- improved customer experience.

# Supporting KPIs include:

- Forecast Accuracy (WAPE)

- Stockout Rate

- Days of Inventory on Hand (DOH)

- Inventory Turns (proxy)

- Overstock Risk

- Lost Sales Proxy

- Holding cost proxy

# Forecasting Methods Used

Demand forecasting was performed using baseline statistical models.

7-Day Moving Average (Chosen Model)

The primary forecasting approach is a 7-day moving average model, which captures short-term demand trends and weekly seasonality.

This model was selected because:

- retail demand often follows weekly patterns

- it is simple and interpretable

- it performs well as a baseline model for operational planning

Forecast performance was evaluated using Weighted Absolute Percentage Error (WAPE).

# ETL Pipeline (How to Run End-to-End)

The ETL pipeline cleans raw retail data and generates curated datasets for forecasting, inventory analysis, and replenishment modeling.

Step 1 — Ensure project folder structure

project/
│
├── raw_data/
│ ├── stores.csv
│ ├── products.json
│ ├── inventory_daily.csv
│ ├── sales_daily.csv
│ ├── purchase_orders.csv
│ └── calendar.csv
│
├── data/ # ETL outputs
├── etl_pipeline.py
├── analysis.ipynb
└── dashboard.twb

Step 2 - Run the ETL script

python etl_pipeline.py

The pipeline:

- cleans and validates raw data

- standardizes store and SKU identifiers

- reconstructs missing inventory values

- flags sales outliers

- generates curated fact tables

When completed, it prints:

ETL completed successfully!

# Curated Outputs Generated

The ETL pipeline generates the following datasets in the data/ folder:

Core Fact Tables - fact_sales_store_sku_daily.csv, fact_inventory_store_sku_daily.csv

Replenishment Inputs - replenishment_inputs_store_sku.csv

Dimension Tables - products_cleaned.csv, stores_cleaned.csv, calendar_cleaned.csv

These datasets are used for forecasting analysis and dashboard visualizations.

# Dashboard

Tool Used: Tableau

To open the dashboard:

1.Open the Tableau workbook file

2.Ensure the data source path points to the /data folder

3.Refresh the data if needed

The dashboard contains four views:

1.Executive Summary – KPIs including Fill Rate and Forecast Accuracy

2.Forecast Explorer – Actual vs forecast demand trends

3.Inventory Risk Monitor – Stockout risk by store and SKU

4.Replenishment Planner – Safety stock, reorder point, and recommended orders
