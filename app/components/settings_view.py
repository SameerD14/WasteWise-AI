from pathlib import Path
from importlib.metadata import version, PackageNotFoundError

import pandas as pd
import streamlit as st
from sqlalchemy import text

from src.database.connection import engine


ROOT = Path(__file__).resolve().parents[2]

MODEL_DIR = ROOT / "models"
REPORT_DIR = ROOT / "monitoring" / "reports"

MODEL_FILES = [
    "expiry_risk_logistic_regression.pkl",
    "expiry_risk_features.pkl",
]

DATA_FILES = [
    ROOT / "data" / "processed" / "ml_preparation_dataset.csv",
    ROOT / "mlflow.db",
]

REPORT_FILES = [
    "data_drift_report.csv",
    "model_performance_report.csv",
    "prediction_data_quality.csv",
    "prediction_status_summary.csv",
    "risk_probability_summary.csv",
    "risk_probability_by_status.csv",
]


def check_database():

    try:
        with engine.connect() as connection:

            connection.execute(text("SELECT 1"))

            tables = [
                "products",
                "inventory_batches",
                "predictions",
                "recommendations",
                "suppliers",
                "purchase_orders",
                "purchase_order_items",
            ]

            results = []

            for table in tables:

                count = connection.execute(
                    text(f"SELECT COUNT(*) FROM `{table}`")
                ).scalar_one()

                results.append({
                    "Table": table,
                    "Records": count,
                    "Status": "Connected",
                })

        return True, pd.DataFrame(results)

    except Exception as error:

        return False, str(error)


def show_settings():

    st.title("Application Settings")

    st.caption(
        "Application configuration, database health, "
        "machine learning resources and monitoring files."
    )

    st.info(
        "This page performs read-only checks. "
        "It does not modify your database, model files or reports."
    )

    # DATABASE STATUS
    st.header("1. Database Health")

    connected, database_result = check_database()

    if connected:

        st.success("MySQL database connection successful.")

        total_records = int(database_result["Records"].sum())

        c1, c2 = st.columns(2)

        c1.metric("Database", "wastewise_ai")
        c2.metric("Total Records Across Tables", f"{total_records:,}")

        st.dataframe(
            database_result,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.error("MySQL connection failed.")

        with st.expander("Technical details"):
            st.code(str(database_result))

    st.divider()

    # MODEL STATUS
    st.header("2. Machine Learning Model Status")

    model_results = []

    for filename in MODEL_FILES:

        path = MODEL_DIR / filename

        model_results.append({
            "Model File": filename,
            "Status": "Available" if path.exists() else "Missing",
            "Size (KB)": round(path.stat().st_size / 1024, 2)
            if path.exists() else None,
        })

    model_df = pd.DataFrame(model_results)

    available_models = sum(
        item["Status"] == "Available"
        for item in model_results
    )

    st.metric(
        "Available Model Files",
        f"{available_models}/{len(MODEL_FILES)}",
    )

    st.dataframe(
        model_df,
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # MLFLOW STATUS
    st.header("3. MLflow Tracking")

    try:
        mlflow_version = version("mlflow")
    except PackageNotFoundError:
        mlflow_version = "Not installed"

    tracking_db = ROOT / "mlflow.db"

    c1, c2, c3 = st.columns(3)

    c1.metric("MLflow Version", mlflow_version)
    c2.metric(
        "Tracking Database",
        "Available" if tracking_db.exists() else "Missing",
    )
    c3.metric("Experiment Name", "WasteWise_Expiry_Risk")

    st.caption(
        "The tracking database is checked for file availability. "
        "This check does not verify individual MLflow runs."
    )

    st.divider()

    # DATA FILES
    st.header("4. Project Data Resources")

    data_results = []

    for path in DATA_FILES:

        data_results.append({
            "Resource": str(path.relative_to(ROOT)),
            "Status": "Available" if path.exists() else "Missing",
        })

    st.dataframe(
        pd.DataFrame(data_results),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # MONITORING REPORTS
    st.header("5. Monitoring Reports")

    report_results = []

    for filename in REPORT_FILES:

        path = REPORT_DIR / filename

        report_results.append({
            "Report": filename,
            "Status": "Available" if path.exists() else "Missing",
            "Size (KB)": round(path.stat().st_size / 1024, 2)
            if path.exists() else None,
        })

    report_df = pd.DataFrame(report_results)

    available_reports = sum(
        item["Status"] == "Available"
        for item in report_results
    )

    st.metric(
        "Available Monitoring Reports",
        f"{available_reports}/{len(REPORT_FILES)}",
    )

    st.dataframe(
        report_df,
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # APPLICATION INFORMATION
    st.header("6. Application Information")

    c1, c2 = st.columns(2)

    c1.metric("Application", "WasteWise AI")
    c2.metric("Version", "1.0")

    st.caption(
        "Smart Inventory Management & Food Waste Prediction"
    )

    st.caption(
        "Model evaluation and monitoring results are based on "
        "historical project data and synthetic expiry-risk labels."
    )
