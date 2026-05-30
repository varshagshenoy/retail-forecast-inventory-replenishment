import pandas as pd
import numpy as np
import re

# ---------- Load data ----------

def load_data():
    stores = pd.read_csv('raw_data/stores.csv')
    products = pd.read_json('raw_data/products.json')
    inventory_daily = pd.read_csv('raw_data/inventory_daily.csv')
    sales_daily = pd.read_csv('raw_data/sales_daily.csv')
    purchase_orders = pd.read_csv('raw_data/purchase_orders.csv')
    calendar = pd.read_csv('raw_data/calendar.csv')

    return stores, products, inventory_daily, sales_daily, purchase_orders, calendar


# ---------- Cleaning and Standardizing the data ----------

def clean_stores(stores):
    stores['region'] = stores['region'].str.lower().str.strip().str.title()
    stores['store_id'] = stores['store_id'].str.upper().str.strip()
    stores['store_size'] = stores['store_size'].str.upper().str.strip()
    stores = stores.drop_duplicates()
    return stores

def clean_products(products):
    products['sku_id'] = products['sku_id'].str.upper().str.strip()
    
    products["category"] = (
        products["category"]
        .str.strip()
        .apply(lambda x: re.sub(r"([a-z])([A-Z])", r"\1 \2", x))
        .str.title()
    )

    numeric_cols = ["price", "cost", "shelf_life_days", "moq_units"]
    for col in numeric_cols:
        products[col] = pd.to_numeric(products[col], errors="coerce")

    products = products.drop_duplicates(subset=['sku_id'])

    products = products[
        (products["price"] > 0) &
        (products["cost"] > 0) &
        (products["moq_units"] > 0) &
        (products["shelf_life_days"] > 0) &
        (products["price"] >= products["cost"])
    ]

    # Flag perishable SKUs
    products["is_perishable"] = products["shelf_life_days"] < 30

    return products
    
def clean_sales_daily(sales_daily):
    sales_daily['date'] = pd.to_datetime(sales_daily['date'])
    sales_daily['store_id'] = sales_daily['store_id'].str.upper().str.strip()
    sales_daily['sku_id'] = sales_daily['sku_id'].str.upper().str.strip()

    sales_daily = sales_daily.drop_duplicates()

    numeric_cols = [
        "units_sold",
        "true_demand_units",
        "stockout_censored_units",
        "revenue",
        "margin_proxy"
    ]
    for col in numeric_cols:
        sales_daily[col] = pd.to_numeric(sales_daily[col], errors="coerce")

    # Remove negative sales
    sales_daily = sales_daily[
        (sales_daily["units_sold"] >= 0) &
        (sales_daily["true_demand_units"] >= 0)
    ]

    # Logical validation: true demand ≥ units sold
    sales_daily = sales_daily[sales_daily["true_demand_units"] >= sales_daily["units_sold"]]

    # Outlier flagging (IQR)
    def compute_upper_bound(x):
        q1 = x.quantile(0.25)
        q3 = x.quantile(0.75)
        iqr = q3 - q1
        return q3 + 1.5 * iqr


    upper_bounds = (
        sales_daily
        .groupby(["store_id", "sku_id"])["units_sold"]
        .transform(compute_upper_bound)
    )

    sales_daily["sales_outlier_flag"] = (
        sales_daily["units_sold"] > upper_bounds
    ).astype(int)

    return sales_daily

def clean_inventory_daily(inventory_daily, sales_daily):
    inventory_daily['date'] = pd.to_datetime(inventory_daily['date'])

    inventory_daily['store_id'] = inventory_daily['store_id'].str.upper().str.strip()
    inventory_daily['sku_id'] = inventory_daily['sku_id'].str.upper().str.strip()

    numeric_cols = ["on_hand_open", "receipts_units", "on_hand_close"]
    for col in numeric_cols:
        inventory_daily[col] = pd.to_numeric(inventory_daily[col], errors="coerce")

    inventory_daily = inventory_daily[
        (inventory_daily["on_hand_open"] >= 0) &
        (inventory_daily["receipts_units"] >= 0)
    ]

    # Merge sales into inventory to get units_sold
    inventory_merged = inventory_daily.merge(
        sales_daily[["date", "store_id", "sku_id", "units_sold"]],
        on=["date", "store_id", "sku_id"],
        how="left"
    )

    # Fill missing units_sold with 0 (if no sales record)
    inventory_merged["units_sold"] = inventory_merged["units_sold"].fillna(0)

    # Identify missing on_hand_close
    missing_mask = inventory_merged["on_hand_close"].isna()

    # Recompute where missing
    inventory_merged.loc[missing_mask, "on_hand_close"] = (
        inventory_merged.loc[missing_mask, "on_hand_open"]
        + inventory_merged.loc[missing_mask, "receipts_units"]
        - inventory_merged.loc[missing_mask, "units_sold"]
    )

    inventory_merged = inventory_merged[inventory_merged["on_hand_close"] >= 0]

    inventory_merged["on_hand_close"] = inventory_merged["on_hand_close"].round().astype("int")

    return inventory_merged.drop(columns=['units_sold'])

def clean_purchase_orders(po):
    po['order_date'] = pd.to_datetime(po['order_date'])
    po['expected_receipt_date'] = pd.to_datetime(po['expected_receipt_date'])

    po["po_id"] = po["po_id"].str.upper().str.strip()
    po["store_id"] = po["store_id"].str.upper().str.strip()
    po["sku_id"] = po["sku_id"].str.upper().str.strip()

    po["order_qty"] = pd.to_numeric(po["order_qty"], errors="coerce")
    po["lead_time_days"] = pd.to_numeric(po["lead_time_days"], errors="coerce")

    po = po.drop_duplicates()

    po = po[(po["order_qty"] > 0) & (po["lead_time_days"] > 0)]

    return po

def clean_calendar(calendar):
    calendar["date"] = pd.to_datetime(calendar["date"])

    # check if flags are integers
    flag_cols = ["is_weekend", "promo_flag", "holiday_flag"]
    for col in flag_cols:
        calendar[col] = pd.to_numeric(calendar[col], errors="coerce")

    # check if binary
    for col in flag_cols:
        calendar = calendar[calendar[col].isin([0, 1])]

    return calendar

# =============================================================
# OUTPUT 1
# =============================================================

def create_fact_sales(sales):
    fact_sales = sales.copy()
    return fact_sales

# =============================================================
# OUTPUT 2
# =============================================================

def create_fact_inventory(inventory, sales):
    max_date = sales["date"].max()
    cutoff = max_date - pd.Timedelta(weeks=4)

    last_4_weeks = sales[sales["date"] >= cutoff]

    avg_4w = (
        last_4_weeks
        .groupby(["store_id", "sku_id"])
        .agg(avg_daily_demand_4w=("true_demand_units", "mean"))
        .reset_index()
    )

    fact_inventory = inventory.merge(
        avg_4w,
        on=["store_id", "sku_id"],
        how="left"
    )

    # on_hand_units
    fact_inventory["on_hand_units"] = fact_inventory["on_hand_close"]

    # stockout flag
    fact_inventory["stockout_flag"] = (
        fact_inventory["on_hand_units"] == 0
    ).astype(int)

    # days of cover
    fact_inventory["days_of_cover"] = (
        fact_inventory["on_hand_units"]
        / fact_inventory["avg_daily_demand_4w"]
    )

    return fact_inventory[[
        "date",
        "store_id",
        "sku_id",
        "on_hand_units",
        "stockout_flag",
        "days_of_cover"
    ]]

# =============================================================
# OUTPUT 3
# =============================================================

def create_replenishment_inputs(sales, purchase_orders):
    # Use last 8 weeks of data for stable demand estimate
    max_date = sales["date"].max()
    cutoff = max_date - pd.Timedelta(weeks=8)

    last_8_weeks = sales[sales["date"] >= cutoff]

    # Compute mean and standard deviation of true demand
    demand_features = (
        last_8_weeks
        .groupby(["store_id", "sku_id"])
        .agg(
            avg_daily_demand=("true_demand_units", "mean"),
            demand_std_dev=("true_demand_units", "std")
        )
        .reset_index()
    )

    # Compute median lead time per store × sku
    lead_time = (
        purchase_orders
        .groupby(["store_id", "sku_id"])
        .agg(lead_time_days=("lead_time_days", "median"))
        .reset_index()
    )

    # Merge demand and lead time
    replenishment = demand_features.merge(
        lead_time,
        on=["store_id", "sku_id"],
        how="left"
    )

    # Handle Missing Values
    # If std is NaN (only 1 observation), assume no variability
    replenishment["demand_std_dev"] = (
        replenishment["demand_std_dev"].fillna(0)
    )

    # If no purchase order history exists, assume lead_time = 0
    # (Conservative fallback — avoids breaking calculations)
    replenishment["lead_time_days"] = (
        replenishment["lead_time_days"].fillna(0)
    )

    # Service level = probability of not stocking out during lead time
    # 95% is standard retail baseline for non-critical items
    replenishment["service_level_target"] = 0.95
    
    # Z-score corresponding to 95% service level (Normal distribution)
    Z = 1.65

    # Safety stock formula:
    # Safety Stock = Z × demand_std_dev × sqrt(lead_time)
    replenishment["safety_stock"] = (
        Z
        * replenishment["demand_std_dev"]
        * np.sqrt(replenishment["lead_time_days"])
    )

    # Reorder Point (ROP) Formula:
    # ROP = (avg_daily_demand × lead_time) + safety_stock
    replenishment["reorder_point"] = (
        replenishment["avg_daily_demand"]
        * replenishment["lead_time_days"]
        + replenishment["safety_stock"]
    )

    # Basic policy: order up to ROP
    replenishment["recommended_order_qty"] = (
        replenishment["reorder_point"]
        .fillna(0)
        .round()
        .astype(int)
    )

    return replenishment


# ---------- Main pipeline ----------

def main():
    stores, products, inventory, sales, purchase_orders, calendar = load_data()

    stores = clean_stores(stores)
    products = clean_products(products)
    sales = clean_sales_daily(sales)
    inventory = clean_inventory_daily(inventory, sales)
    purchase_orders = clean_purchase_orders(purchase_orders)
    calendar = clean_calendar(calendar)

    fact_sales = create_fact_sales(sales)
    fact_inventory = create_fact_inventory(inventory, sales)
    replenishment_inputs = create_replenishment_inputs(sales, purchase_orders)

    fact_sales.to_csv('data/fact_sales_store_sku_daily.csv', index=False)
    fact_inventory.to_csv('data/fact_inventory_store_sku_daily.csv', index=False)
    replenishment_inputs.to_csv('data/replenishment_inputs_store_sku.csv', index=False)
    products.to_csv("data/products_cleaned.csv", index=False)
    stores.to_csv("data/stores_cleaned.csv", index=False)
    calendar.to_csv("data/calendar_cleaned.csv", index=False)

    print('ETL completed successfully!')


if __name__ == "__main__":
    main()