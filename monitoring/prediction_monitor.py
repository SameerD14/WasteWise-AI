
"""
WasteWise AI - Prediction Monitoring

Monitors:
1. Prediction status distribution
2. Risk probability statistics
3. Missing values
4. Prediction data quality
5. Prediction distribution chart

Note: This analyzes an existing historical prediction file.
It is not live production monitoring.
"""

from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


# --------------------------------------------------
# 1. PROJECT PATHS
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

PREDICTION_PATH = (
    PROJECT_ROOT
    / "data"
    / "predictions"
    / "expiry_risk_predictions.csv"
)

REPORT_DIR = PROJECT_ROOT / "monitoring" / "reports"
PLOT_DIR = PROJECT_ROOT / "monitoring" / "plots"

REPORT_DIR.mkdir(parents=True, exist_ok=True)
PLOT_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# 2. LOAD PREDICTIONS
# --------------------------------------------------

def load_predictions():

    print("\nLoading prediction dataset...")

    if not PREDICTION_PATH.exists():
        raise FileNotFoundError(
            f"Prediction file not found: {PREDICTION_PATH}"
        )

    df = pd.read_csv(PREDICTION_PATH)

    required_columns = [
        "batch_id",
        "risk_status",
        "risk_probability",
        "action",
    ]

    missing_columns = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing columns: {missing_columns}"
        )

    print("Prediction dataset loaded!")
    print("Total predictions:", len(df))

    return df


# --------------------------------------------------
# 3. DATA QUALITY CHECK
# --------------------------------------------------

def check_data_quality(df):

    print("\nChecking prediction data quality...")

    missing_values = df.isnull().sum()

    duplicate_batches = df["batch_id"].duplicated().sum()

    invalid_probabilities = (
        df["risk_probability"].notna()
        & ~df["risk_probability"].between(0, 100)
    ).sum()

    quality_results = pd.DataFrame({
        "check": [
            "Total prediction records",
            "Missing batch IDs",
            "Missing risk probabilities",
            "Duplicate batch IDs",
            "Invalid risk probabilities",
        ],
        "result": [
            len(df),
            int(missing_values["batch_id"]),
            int(missing_values["risk_probability"]),
            int(duplicate_batches),
            int(invalid_probabilities),
        ],
    })

    print(quality_results.to_string(index=False))

    quality_path = (
        REPORT_DIR / "prediction_data_quality.csv"
    )

    quality_results.to_csv(
        quality_path,
        index=False
    )

    return quality_results


# --------------------------------------------------
# 4. MONITOR PREDICTION DISTRIBUTION
# --------------------------------------------------

def monitor_predictions(df):

    print("\nMonitoring prediction distribution...")

    status_counts = (
        df["risk_status"]
        .value_counts()
        .rename_axis("risk_status")
        .reset_index(name="batch_count")
    )

    status_counts["percentage"] = (
        status_counts["batch_count"]
        / len(df)
        * 100
    )

    print("\nPrediction Status:")
    print(status_counts.to_string(index=False))

    status_path = (
        REPORT_DIR / "prediction_status_summary.csv"
    )

    status_counts.to_csv(
        status_path,
        index=False
    )

    return status_counts


# --------------------------------------------------
# 5. MONITOR RISK PROBABILITY
# --------------------------------------------------

def monitor_risk_probability(df):

    print("\nMonitoring risk probabilities...")

    valid_probabilities = (
        pd.to_numeric(
            df["risk_probability"],
            errors="coerce"
        )
    )

    valid_probabilities = valid_probabilities.dropna()

    if not valid_probabilities.between(0, 100).all():
        raise ValueError(
            "Risk probabilities must be between 0 and 100."
        )

    probability_summary = pd.DataFrame({
        "metric": [
            "Total predictions",
            "Valid risk probabilities",
            "Missing risk probabilities",
            "Average risk probability",
            "Median risk probability",
            "Minimum risk probability",
            "Maximum risk probability",
            "Standard deviation",
        ],
        "value": [
            len(df),
            len(valid_probabilities),
            int(df["risk_probability"].isna().sum()),
            valid_probabilities.mean(),
            valid_probabilities.median(),
            valid_probabilities.min(),
            valid_probabilities.max(),
            valid_probabilities.std(),
        ],
    })

    print(probability_summary.to_string(index=False))

    probability_path = (
        REPORT_DIR / "risk_probability_summary.csv"
    )

    probability_summary.to_csv(
        probability_path,
        index=False
    )

    return valid_probabilities


# --------------------------------------------------
# 6. AVERAGE PROBABILITY BY STATUS
# --------------------------------------------------

def probability_by_status(df):

    summary = (
        df.groupby("risk_status")["risk_probability"]
        .agg(["count", "mean", "min", "max"])
        .reset_index()
    )

    print("\nRisk Probability by Status:")
    print(summary.to_string(index=False))

    output_path = (
        REPORT_DIR / "risk_probability_by_status.csv"
    )

    summary.to_csv(
        output_path,
        index=False
    )


# --------------------------------------------------
# 7. CREATE PREDICTION CHART
# --------------------------------------------------

def create_prediction_chart(status_counts):

    print("\nCreating prediction distribution chart...")

    plt.figure(figsize=(10, 6))

    plt.bar(
        status_counts["risk_status"],
        status_counts["batch_count"]
    )

    plt.title(
        "WasteWise AI - Prediction Distribution"
    )

    plt.xlabel("Prediction Status")
    plt.ylabel("Number of Inventory Batches")

    plt.xticks(rotation=20, ha="right")

    plt.tight_layout()

    chart_path = (
        PLOT_DIR / "prediction_distribution.png"
    )

    plt.savefig(
        chart_path,
        dpi=150
    )

    plt.close()

    print("Chart saved:", chart_path)


# --------------------------------------------------
# 8. MAIN FUNCTION
# --------------------------------------------------

def main():

    print("=" * 60)
    print("WASTEWISE AI - PREDICTION MONITORING")
    print("=" * 60)

    df = load_predictions()

    check_data_quality(df)

    status_counts = monitor_predictions(df)

    monitor_risk_probability(df)

    probability_by_status(df)

    create_prediction_chart(status_counts)

    print("\n" + "=" * 60)
    print("PREDICTION MONITORING COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()
