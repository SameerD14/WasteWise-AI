
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd

from mlflow.models import infer_signature


# ==========================================
# 1. PROJECT PATHS
# ==========================================

PROJECT_DIR = Path(__file__).resolve().parents[2]

MODEL_FILE = (
    PROJECT_DIR
    / "models"
    / "expiry_risk_logistic_regression.pkl"
)

FEATURES_FILE = (
    PROJECT_DIR
    / "models"
    / "expiry_risk_features.pkl"
)

DATA_FILE = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "ml_preparation_dataset.csv"
)

DATABASE_FILE = PROJECT_DIR / "mlflow.db"


# ==========================================
# 2. MODEL FEATURES
# ==========================================

FEATURE_COLUMNS = [
    "quantity_remaining",
    "initial_quantity",
    "days_to_expiry",
    "avg_daily_sales_7d",
    "expected_demand_before_expiry",
    "unit_price",
    "unit_cost",
    "discount_pct",
    "stock_coverage_days",
    "remaining_stock_pct",
    "profit_per_unit",
    "gross_margin_pct"
]

TARGET_COLUMN = "expiry_risk_label"


# ==========================================
# 3. PREVIOUSLY RECORDED TEST METRICS
# ==========================================

TEST_METRICS = {
    "accuracy": 0.8889,
    "precision": 0.8851,
    "recall": 0.9390,
    "f1_score": 0.9112,
    "roc_auc": 0.9535,
    "pr_auc": 0.9672
}


# ==========================================
# 4. CHECK REQUIRED FILES
# ==========================================

def check_files():

    required_files = [
        MODEL_FILE,
        FEATURES_FILE,
        DATA_FILE
    ]

    for file in required_files:

        if not file.exists():
            raise FileNotFoundError(
                f"Required file not found: {file}"
            )


# ==========================================
# 5. MAIN MLFLOW FUNCTION
# ==========================================

def main():

    print("\nStarting WasteWise AI MLflow tracking...\n")

    check_files()

    # Configure local SQLite tracking database
    tracking_uri = (
        f"sqlite:///{DATABASE_FILE.as_posix()}"
    )

    mlflow.set_tracking_uri(tracking_uri)

    # Create or select experiment
    experiment_name = "WasteWise_Expiry_Risk"

    mlflow.set_experiment(experiment_name)

    print("MLflow experiment:", experiment_name)

    # Load existing trained model
    model = joblib.load(MODEL_FILE)

    print("Existing Logistic Regression model loaded.")

    # Load dataset for model input example
    dataset = pd.read_csv(DATA_FILE)

    missing_columns = [
        col for col in FEATURE_COLUMNS
        if col not in dataset.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing model features: {missing_columns}"
        )

    if TARGET_COLUMN not in dataset.columns:
        raise ValueError(
            f"Target column not found: {TARGET_COLUMN}"
        )

    X = dataset[FEATURE_COLUMNS]

    # Use sample records only for input signature
    input_example = X.head(5).copy()

    if input_example.empty:
        raise ValueError("The input dataset is empty.")

    # Verify that the saved model can make predictions
    predictions = model.predict(input_example)

    signature = infer_signature(
        input_example,
        predictions
    )

    print("Model input validation successful.")

    # ======================================
    # 6. START MLFLOW EXPERIMENT
    # ======================================

    with mlflow.start_run(
        run_name="Logistic_Regression_Baseline"
    ) as run:

        # Log parameters
        mlflow.log_params({
            "model_type": "Logistic Regression",
            "target": TARGET_COLUMN,
            "number_of_features": len(FEATURE_COLUMNS),
            "training_dataset": "ml_preparation_dataset.csv",
            "validation_method": "Previously evaluated temporal split",
            "test_split_cutoff": "2026-10-07"
        })

        # Log previously recorded evaluation metrics
        mlflow.log_metrics(TEST_METRICS)

        # Log useful tags
        mlflow.set_tags({
            "project": "WasteWise AI",
            "model_category": "Classification",
            "experiment_type": "Expiry Risk Prediction",
            "data_type": "Synthetic labels",
            "model_status": "Previously evaluated baseline"
        })

        # Save existing trained model in MLflow
        mlflow.sklearn.log_model(
            sk_model=model,
            name="expiry_risk_logistic_regression",
            signature=signature,
            input_example=input_example
        )

        # Save feature metadata as an artifact
        mlflow.log_artifact(
            str(FEATURES_FILE),
            artifact_path="model_metadata"
        )

        print("\nMLflow experiment recorded successfully!")

        print("Run ID:", run.info.run_id)

        print("Experiment ID:", run.info.experiment_id)

    print("\nTracking database:", DATABASE_FILE)

    print("\nMLflow tracking completed successfully!")


# ==========================================
# 7. RUN PROGRAM
# ==========================================

if __name__ == "__main__":
    main()
