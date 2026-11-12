
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from src.database.connection import engine


# ==========================================
# 1. PROJECT PATHS
# ==========================================

PROJECT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_DIR / "data"

PRODUCTS_FILE = DATA_DIR / "raw" / "products.csv"
INVENTORY_FILE = DATA_DIR / "processed" / "inventory_features.csv"
PREDICTIONS_FILE = DATA_DIR / "predictions" / "expiry_risk_predictions.csv"
RECOMMENDATIONS_FILE = DATA_DIR / "predictions" / "inventory_recommendations.csv"


# ==========================================
# 2. CSV LOADING FUNCTION
# ==========================================

def load_csv(file_path):

    if not file_path.exists():
        raise FileNotFoundError(
            f"CSV file not found: {file_path}"
        )

    print(f"Reading: {file_path.name}")

    return pd.read_csv(file_path)


# ==========================================
# 3. MAIN DATA LOADING FUNCTION
# ==========================================

def main():

    print("\nStarting WasteWise AI data loading...\n")

    # --------------------------------------
    # STEP 1: Read CSV files
    # --------------------------------------

    products_df = load_csv(PRODUCTS_FILE)

    inventory_df = load_csv(INVENTORY_FILE)

    predictions_df = load_csv(PREDICTIONS_FILE)

    recommendations_df = load_csv(RECOMMENDATIONS_FILE)


    # --------------------------------------
    # STEP 2: Define MySQL table columns
    # --------------------------------------

    product_columns = [
        "product_id",
        "product_name",
        "category",
        "shelf_life_days",
        "selling_price",
        "unit_cost"
    ]

    inventory_columns = [
        "batch_id",
        "product_id",
        "category",
        "snapshot_date",
        "expiry_date",
        "initial_quantity",
        "quantity_remaining",
        "days_to_expiry",
        "avg_daily_sales_7d",
        "expected_demand_before_expiry",
        "inventory_surplus",
        "stock_coverage_days",
        "unit_price",
        "unit_cost",
        "discount_pct"
    ]

    prediction_columns = [
        "batch_id",
        "risk_status",
        "risk_probability"
    ]

    recommendation_columns = [
        "batch_id",
        "priority",
        "recommended_action"
    ]


    # --------------------------------------
    # STEP 3: Check required CSV columns
    # --------------------------------------

    datasets = [
        ("products", products_df, product_columns),
        ("inventory batches", inventory_df, inventory_columns),
        ("predictions", predictions_df, prediction_columns),
        ("recommendations", recommendations_df, recommendation_columns)
    ]

    for name, df, required_columns in datasets:

        missing_columns = [
            column for column in required_columns
            if column not in df.columns
        ]

        if missing_columns:
            raise ValueError(
                f"Missing columns in {name} CSV: {missing_columns}"
            )

        print(f"{name}: required columns verified")


    # --------------------------------------
    # STEP 4: Select required columns
    # --------------------------------------

    products_df = products_df[product_columns].copy()

    inventory_df = inventory_df[inventory_columns].copy()

    predictions_df = predictions_df[prediction_columns].copy()

    recommendations_df = recommendations_df[recommendation_columns].copy()


    # --------------------------------------
    # STEP 5: Convert date columns
    # --------------------------------------

    inventory_df["snapshot_date"] = pd.to_datetime(
        inventory_df["snapshot_date"],
        errors="raise"
    ).dt.date

    inventory_df["expiry_date"] = pd.to_datetime(
        inventory_df["expiry_date"],
        errors="raise"
    ).dt.date


    # --------------------------------------
    # STEP 6: Check duplicate primary keys
    # --------------------------------------

    datasets_to_check = [
        ("products", products_df, "product_id"),
        ("inventory batches", inventory_df, "batch_id"),
        ("predictions", predictions_df, "batch_id"),
        ("recommendations", recommendations_df, "batch_id")
    ]

    for name, df, primary_key in datasets_to_check:

        if df[primary_key].duplicated().any():

            raise ValueError(
                f"Duplicate primary keys found in {name} CSV."
            )

        print(f"{name}: primary keys verified")


    # --------------------------------------
    # STEP 7: Validate product references
    # --------------------------------------

    product_ids = set(products_df["product_id"])

    inventory_product_ids = set(inventory_df["product_id"])

    invalid_product_ids = inventory_product_ids - product_ids

    if invalid_product_ids:
        raise ValueError(
            f"Inventory contains unknown product IDs: {invalid_product_ids}"
        )


    # --------------------------------------
    # STEP 8: Validate batch references
    # --------------------------------------

    inventory_batch_ids = set(inventory_df["batch_id"])

    prediction_batch_ids = set(predictions_df["batch_id"])

    recommendation_batch_ids = set(recommendations_df["batch_id"])

    if prediction_batch_ids != inventory_batch_ids:
        raise ValueError(
            "Prediction batch IDs do not match inventory batch IDs."
        )

    if recommendation_batch_ids != inventory_batch_ids:
        raise ValueError(
            "Recommendation batch IDs do not match inventory batch IDs."
        )


    # --------------------------------------
    # STEP 9: Load data into MySQL
    # --------------------------------------

    print("\nConnecting to MySQL...")

    with engine.begin() as connection:

        # Delete child tables before parent tables
        connection.execute(
            text("DELETE FROM recommendations")
        )

        connection.execute(
            text("DELETE FROM predictions")
        )

        connection.execute(
            text("DELETE FROM inventory_batches")
        )

        connection.execute(
            text("DELETE FROM products")
        )

        print("Existing table records cleared.")

        # Insert products first
        products_df.to_sql(
            "products",
            con=connection,
            if_exists="append",
            index=False
        )

        print("Products inserted successfully.")

        # Insert inventory batches
        inventory_df.to_sql(
            "inventory_batches",
            con=connection,
            if_exists="append",
            index=False
        )

        print("Inventory batches inserted successfully.")

        # Insert predictions
        predictions_df.to_sql(
            "predictions",
            con=connection,
            if_exists="append",
            index=False
        )

        print("Predictions inserted successfully.")

        # Insert recommendations
        recommendations_df.to_sql(
            "recommendations",
            con=connection,
            if_exists="append",
            index=False
        )

        print("Recommendations inserted successfully.")


        # ----------------------------------
        # STEP 10: Verify MySQL row counts
        # ----------------------------------

        print("\n========== DATABASE SUMMARY ==========")

        tables = [
            "products",
            "inventory_batches",
            "predictions",
            "recommendations"
        ]

        for table in tables:

            count = connection.execute(
                text(f"SELECT COUNT(*) FROM {table}")
            ).scalar_one()

            print(f"{table}: {count} rows")

        print("======================================")

    print("\nWasteWise AI data loading completed successfully!")


# ==========================================
# 4. RUN PROGRAM
# ==========================================

if __name__ == "__main__":
    main()
