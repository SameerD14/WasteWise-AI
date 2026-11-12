
from pathlib import Path

import joblib
import pandas as pd


# Project paths
PROJECT_DIR = Path(__file__).resolve().parents[2]
MODEL_DIR = PROJECT_DIR / "models"

MODEL_PATH = MODEL_DIR / "expiry_risk_logistic_regression.pkl"
FEATURES_PATH = MODEL_DIR / "expiry_risk_features.pkl"


# Load saved model and feature names
model = joblib.load(MODEL_PATH)
model_features = joblib.load(FEATURES_PATH)


def predict_inventory_risk(batch_data: pd.DataFrame) -> pd.DataFrame:
    """
    Predict synthetic expiry-risk labels for inventory batches.

    Expired batches are blocked from sale recommendations.
    Batches expiring today are sent for immediate review.
    """

    results = []

    for index, batch in batch_data.iterrows():

        batch_id = batch.get("batch_id", index)
        days = pd.to_numeric(
            pd.Series([batch.get("days_to_expiry")]),
            errors="coerce"
        ).iloc[0]

        # Safety rule 1: expired batches
        if pd.isna(days):
            results.append({
                "batch_id": batch_id,
                "risk_status": "Data Incomplete",
                "risk_probability": None,
                "action": "Check missing expiry information"
            })
            continue

        if days < 0:
            results.append({
                "batch_id": batch_id,
                "risk_status": "Expired",
                "risk_probability": None,
                "action": "Do not sell. Follow food-safety disposal policy."
            })
            continue

        # Safety rule 2: expiry today
        if days == 0:
            results.append({
                "batch_id": batch_id,
                "risk_status": "Expires Today - Immediate Review",
                "risk_probability": None,
                "action": "Immediate manager and food-safety review"
            })
            continue

        # Prepare exactly the features used during training
        missing_columns = [
            col for col in model_features
            if col not in batch_data.columns
        ]

        if missing_columns:
            raise ValueError(
                f"Missing required model features: {missing_columns}"
            )

        sample = pd.DataFrame(
            [batch[model_features].to_dict()],
            columns=model_features
        )

        # Convert features to numeric values
        sample = sample.apply(pd.to_numeric, errors="coerce")

        # Do not predict when required input values are missing
        if sample.isna().any().any():
            results.append({
                "batch_id": batch_id,
                "risk_status": "Data Incomplete",
                "risk_probability": None,
                "action": "Complete missing inventory data before prediction"
            })
            continue

        # Model prediction
        prediction = model.predict(sample)[0]
        probability = model.predict_proba(sample)[0][1]

        if prediction == 1:
            status = "High Risk"
            action = "Review stock and demand; assess safe inventory actions"
        else:
            status = "Low Risk"
            action = "Continue inventory monitoring"

        results.append({
            "batch_id": batch_id,
            "risk_status": status,
            "risk_probability": round(float(probability) * 100, 2),
            "action": action
        })

    return pd.DataFrame(results)
