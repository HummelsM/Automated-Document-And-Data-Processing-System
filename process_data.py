from flask import Flask, request, jsonify
import pandas as pd
from io import StringIO

app = Flask(__name__)


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "running",
        "service": "Automated Data Processing API"
    })


@app.route("/process-data", methods=["POST"])
def process_data():

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "error": "Missing JSON payload"
            }), 400

        csv_content = data.get("csv_data")

        if not csv_content:
            return jsonify({
                "error": "csv_data field is required"
            }), 400

        # -----------------------------
        # Load CSV into DataFrame
        # -----------------------------
        df = pd.read_csv(StringIO(csv_content))

        original_rows = len(df)

        # -----------------------------
        # Missing Values
        # -----------------------------
        missing_customer_ids = df["Customer_ID"].isna().sum()
        missing_revenue = df["Revenue"].isna().sum()

        # -----------------------------
        # Duplicate Detection
        # -----------------------------
        duplicate_rows = df.duplicated().sum()

        # -----------------------------
        # Clean Data
        # -----------------------------
        df["Region"] = (
            df["Region"]
            .astype(str)
            .str.strip()
            .str.title()
        )

        # Fill missing revenue with 0
        df["Revenue"] = pd.to_numeric(
            df["Revenue"],
            errors="coerce"
        ).fillna(0)

        # Remove duplicates
        df = df.drop_duplicates()

        cleaned_rows = len(df)

        # -----------------------------
        # KPIs
        # -----------------------------
        total_revenue = round(df["Revenue"].sum(), 2)

        average_revenue = round(
            df["Revenue"].mean(),
            2
        )

        unique_customers = (
            df["Customer_Name"]
            .nunique()
        )

        # -----------------------------
        # Revenue By Region
        # -----------------------------
        revenue_by_region = (
            df.groupby("Region")["Revenue"]
            .sum()
            .round(2)
            .to_dict()
        )

        # Highest Revenue Region
        top_region = max(
            revenue_by_region,
            key=revenue_by_region.get
        )

        # -----------------------------
        # Response
        # -----------------------------
        response = {
            "status": "success",

            "data_quality": {
                "original_rows": int(original_rows),
                "cleaned_rows": int(cleaned_rows),
                "duplicate_rows": int(duplicate_rows),
                "missing_customer_ids": int(missing_customer_ids),
                "missing_revenue": int(missing_revenue)
            },

            "kpis": {
                "total_revenue": total_revenue,
                "average_revenue": average_revenue,
                "unique_customers": int(unique_customers),
                "top_region": top_region
            },

            "revenue_by_region": revenue_by_region
        }

        return jsonify(response), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
