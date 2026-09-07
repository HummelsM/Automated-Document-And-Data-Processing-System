from flask import Flask, request, jsonify, send_from_directory
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import uuid
import os


app = Flask(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

BASE_OUTPUT_DIR = Path("output")
BASE_OUTPUT_DIR.mkdir(exist_ok=True)


# ============================================================
# PROCESS SALES DATA
# ============================================================

def process_sales_data(data):

    """
    Process sales data and return structured results
    suitable for Make, Zapier, Gemini, etc.
    """

    # --------------------------------------------------------
    # Convert incoming data to DataFrame
    # --------------------------------------------------------

    df = pd.DataFrame(data)

    original_rows = len(df)

    if df.empty:
        raise ValueError("No data was provided.")

    # --------------------------------------------------------
    # Standardize column names
    # --------------------------------------------------------

    df.columns = (
        df.columns
        .str.strip()
        .str.replace(" ", "_", regex=False)
    )

    # --------------------------------------------------------
    # Check required columns
    # --------------------------------------------------------

    required_columns = [
        "Order_ID",
        "Date",
        "Customer_ID",
        "Product",
        "Category",
        "Region",
        "Quantity",
        "Unit_Price",
        "Discount",
        "Sales",
        "Payment_Method",
        "Salesperson"
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:

        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    # ========================================================
    # DATA CLEANING
    # ========================================================

    # --------------------------------------------------------
    # Remove duplicates
    # --------------------------------------------------------

    duplicates_removed = int(
        df.duplicated().sum()
    )

    df = df.drop_duplicates()

    # --------------------------------------------------------
    # Convert data types
    # --------------------------------------------------------

    df["Date"] = pd.to_datetime(
        df["Date"],
        errors="coerce"
    )

    numeric_columns = [
        "Quantity",
        "Unit_Price",
        "Discount",
        "Sales"
    ]

    for column in numeric_columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    # --------------------------------------------------------
    # Clean text columns
    # --------------------------------------------------------

    text_columns = [
        "Product",
        "Category",
        "Region",
        "Payment_Method",
        "Salesperson"
    ]

    for column in text_columns:

        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
            .str.title()
        )

    # --------------------------------------------------------
    # Standardize product names
    # --------------------------------------------------------

    product_mapping = {
        "Laptop": "Laptop",
        "Monitor": "Monitor",
        "Keyboard": "Keyboard",
        "Mouse": "Mouse",
        "Headphones": "Headphones",
        "Tablet": "Tablet",
        "Webcam": "Webcam",
        "Printer": "Printer"
    }

    df["Product"] = df["Product"].replace(
        product_mapping
    )

    # --------------------------------------------------------
    # Missing products
    # --------------------------------------------------------

    missing_products = int(
        df["Product"].isna().sum()
    )

    df = df.dropna(
        subset=["Product"]
    )

    # --------------------------------------------------------
    # Missing regions
    # --------------------------------------------------------

    missing_regions = int(
        df["Region"].isna().sum()
    )

    df["Region"] = df["Region"].fillna(
        "Unknown"
    )

    # --------------------------------------------------------
    # Missing unit prices
    # --------------------------------------------------------

    missing_unit_prices = int(
        df["Unit_Price"].isna().sum()
    )

    product_median_prices = (
        df.groupby("Product")["Unit_Price"]
        .transform("median")
    )

    df["Unit_Price"] = (
        df["Unit_Price"]
        .fillna(product_median_prices)
    )

    # --------------------------------------------------------
    # Missing quantities
    # --------------------------------------------------------

    missing_quantities = int(
        df["Quantity"].isna().sum()
    )

    df["Quantity"] = (
        df["Quantity"]
        .fillna(1)
    )

    # --------------------------------------------------------
    # Invalid quantities
    # --------------------------------------------------------

    invalid_quantities = int(
        (df["Quantity"] <= 0).sum()
    )

    df.loc[
        df["Quantity"] <= 0,
        "Quantity"
    ] = 1

    # --------------------------------------------------------
    # Missing discounts
    # --------------------------------------------------------

    missing_discounts = int(
        df["Discount"].isna().sum()
    )

    df["Discount"] = (
        df["Discount"]
        .fillna(0)
    )

    # --------------------------------------------------------
    # Recalculate sales
    # --------------------------------------------------------

    df["Sales"] = (
        df["Unit_Price"]
        * df["Quantity"]
        * (1 - df["Discount"])
    )

    df["Sales"] = df["Sales"].round(2)

    # --------------------------------------------------------
    # Invalid dates
    # --------------------------------------------------------

    invalid_dates = int(
        df["Date"].isna().sum()
    )

    df = df.dropna(
        subset=["Date"]
    )

    if df.empty:
        raise ValueError(
            "No valid records remain after cleaning."
        )

    # ========================================================
    # KPI ANALYSIS
    # ========================================================

    total_sales = float(
        df["Sales"].sum()
    )

    total_orders = int(
        df["Order_ID"].nunique()
    )

    total_quantity = float(
        df["Quantity"].sum()
    )

    average_order_value = (
        total_sales / total_orders
        if total_orders > 0
        else 0
    )

    # --------------------------------------------------------
    # Product analysis
    # --------------------------------------------------------

    product_sales = (
        df.groupby("Product")["Sales"]
        .sum()
        .sort_values(ascending=False)
    )

    top_product = (
        product_sales.index[0]
        if not product_sales.empty
        else None
    )

    top_product_sales = (
        float(product_sales.iloc[0])
        if not product_sales.empty
        else 0
    )

    # --------------------------------------------------------
    # Region analysis
    # --------------------------------------------------------

    region_sales = (
        df.groupby("Region")["Sales"]
        .sum()
        .sort_values(ascending=False)
    )

    top_region = (
        region_sales.index[0]
        if not region_sales.empty
        else None
    )

    top_region_sales = (
        float(region_sales.iloc[0])
        if not region_sales.empty
        else 0
    )

    # --------------------------------------------------------
    # Salesperson analysis
    # --------------------------------------------------------

    salesperson_sales = (
        df.groupby("Salesperson")["Sales"]
        .sum()
        .sort_values(ascending=False)
    )

    top_salesperson = (
        salesperson_sales.index[0]
        if not salesperson_sales.empty
        else None
    )

    # --------------------------------------------------------
    # Category analysis
    # --------------------------------------------------------

    category_sales = (
        df.groupby("Category")["Sales"]
        .sum()
        .sort_values(ascending=False)
    )

    # --------------------------------------------------------
    # Average discount
    # --------------------------------------------------------

    average_discount = float(
        df["Discount"].mean() * 100
    )

    # --------------------------------------------------------
    # Reporting period
    # --------------------------------------------------------

    start_date = df["Date"].min()
    end_date = df["Date"].max()

    # ========================================================
    # GENERATE CHARTS
    # ========================================================

    run_id = str(uuid.uuid4())

    run_dir = (
        BASE_OUTPUT_DIR / run_id
    )

    run_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Sales by Product
    # --------------------------------------------------------

    plt.figure(figsize=(10, 6))

    product_sales.sort_values().plot(
        kind="barh"
    )

    plt.title(
        "Sales by Product",
        fontsize=16
    )

    plt.xlabel("Sales ($)")
    plt.ylabel("Product")

    plt.tight_layout()

    plt.savefig(
        run_dir / "sales_by_product.png",
        dpi=150
    )

    plt.close()

    # --------------------------------------------------------
    # Sales by Region
    # --------------------------------------------------------

    plt.figure(figsize=(8, 5))

    region_sales.plot(
        kind="bar"
    )

    plt.title(
        "Sales by Region",
        fontsize=16
    )

    plt.xlabel("Region")
    plt.ylabel("Sales ($)")

    plt.xticks(rotation=0)

    plt.tight_layout()

    plt.savefig(
        run_dir / "sales_by_region.png",
        dpi=150
    )

    plt.close()

    # --------------------------------------------------------
    # Daily Sales Trend
    # --------------------------------------------------------

    daily_sales = (
        df.groupby("Date")["Sales"]
        .sum()
    )

    plt.figure(figsize=(11, 5))

    daily_sales.plot(
        kind="line"
    )

    plt.title(
        "Daily Sales Trend",
        fontsize=16
    )

    plt.xlabel("Date")
    plt.ylabel("Sales ($)")

    plt.tight_layout()

    plt.savefig(
        run_dir / "daily_sales_trend.png",
        dpi=150
    )

    plt.close()

    # --------------------------------------------------------
    # Sales by Category
    # --------------------------------------------------------

    plt.figure(figsize=(9, 5))

    category_sales.plot(
        kind="bar"
    )

    plt.title(
        "Sales by Category",
        fontsize=16
    )

    plt.xlabel("Category")
    plt.ylabel("Sales ($)")

    plt.xticks(rotation=20)

    plt.tight_layout()

    plt.savefig(
        run_dir / "sales_by_category.png",
        dpi=150
    )

    plt.close()

    # ========================================================
    # STRUCTURED RESULT
    # ========================================================

    result = {

        "status": "success",

        "run_id": run_id,

        # ----------------------------------------------------
        # Data Quality
        # ----------------------------------------------------

        "data_quality": {

            "rows_received":
                original_rows,

            "rows_processed":
                len(df),

            "rows_removed":
                original_rows - len(df),

            "duplicates_removed":
                duplicates_removed,

            "missing_products_removed":
                missing_products,

            "missing_regions_fixed":
                missing_regions,

            "missing_unit_prices_fixed":
                missing_unit_prices,

            "missing_quantities_fixed":
                missing_quantities,

            "invalid_quantities_corrected":
                invalid_quantities,

            "missing_discounts_fixed":
                missing_discounts,

            "invalid_dates_removed":
                invalid_dates
        },

        # ----------------------------------------------------
        # KPIs
        # ----------------------------------------------------

        "kpis": {

            "total_sales":
                round(total_sales, 2),

            "total_orders":
                total_orders,

            "total_units_sold":
                round(total_quantity, 2),

            "average_order_value":
                round(average_order_value, 2),

            "average_discount_percent":
                round(average_discount, 2)
        },

        # ----------------------------------------------------
        # Top Performers
        # ----------------------------------------------------

        "top_performers": {

            "top_product":
                top_product,

            "top_product_sales":
                round(top_product_sales, 2),

            "top_region":
                top_region,

            "top_region_sales":
                round(top_region_sales, 2),

            "top_salesperson":
                top_salesperson
        },

        # ----------------------------------------------------
        # Detailed Breakdowns
        # ----------------------------------------------------

        "sales_by_product": {

            str(k):
                round(float(v), 2)

            for k, v in product_sales.items()
        },

        "sales_by_region": {

            str(k):
                round(float(v), 2)

            for k, v in region_sales.items()
        },

        "sales_by_category": {

            str(k):
                round(float(v), 2)

            for k, v in category_sales.items()
        },

        # ----------------------------------------------------
        # Reporting Period
        # ----------------------------------------------------

        "reporting_period": {

            "start":
                start_date.strftime("%Y-%m-%d"),

            "end":
                end_date.strftime("%Y-%m-%d")
        },

        # ----------------------------------------------------
        # Generated Charts
        # ----------------------------------------------------

        "charts": {

            "sales_by_product":
                f"/charts/{run_id}/sales_by_product.png",

            "sales_by_region":
                f"/charts/{run_id}/sales_by_region.png",

            "daily_sales_trend":
                f"/charts/{run_id}/daily_sales_trend.png",

            "sales_by_category":
                f"/charts/{run_id}/sales_by_category.png"
        }
    }

    return result


# ============================================================
# PROCESS SALES API
# ============================================================

@app.route(
    "/api/process-sales",
    methods=["POST"]
)
def process_sales():

    try:

        payload = request.get_json()

        if not payload:

            return jsonify({
                "status": "error",
                "message": "No JSON data received."
            }), 400

        # Accept:
        #
        # {
        #     "records": [...]
        # }
        #
        # or:
        #
        # [...]

        if isinstance(payload, dict):

            records = payload.get("records")

        else:

            records = payload

        if not records:

            return jsonify({
                "status": "error",
                "message": "No records were provided."
            }), 400

        result = process_sales_data(
            records
        )

        return jsonify(
            result
        ), 200

    except Exception as e:

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# ============================================================
# CHART FILE ENDPOINT
# ============================================================

@app.route(
    "/charts/<run_id>/<filename>",
    methods=["GET"]
)
def get_chart(
    run_id,
    filename
):

    run_dir = (
        BASE_OUTPUT_DIR / run_id
    )

    return send_from_directory(
        run_dir,
        filename
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route(
    "/",
    methods=["GET"]
)
def home():

    return jsonify({

        "status": "online",

        "service":
            "Automated Sales Data Processing API",

        "endpoint":
            "/api/process-sales"
    })


@app.route(
    "/test",
    methods=["GET"]
)
def test():

    return jsonify({

        "status": "success",

        "message":
            "API is working."
    })


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
