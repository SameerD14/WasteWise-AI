
"""
WasteWise AI - Model Performance Monitoring

Reads previously recorded evaluation metrics from MLflow.

Important:
These are historical test evaluation metrics,
not newly measured live production metrics.
"""

from pathlib import Path

import mlflow
import pandas as pd
import matplotlib.pyplot as plt

from mlflow.tracking import MlflowClient


# --------------------------------------------------
# 1. PROJECT PATHS
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATABASE_FILE = PROJECT_ROOT / "mlflow.db"

REPORT_DIR = PROJECT_ROOT / "monitoring" / "reports"
PLOT_DIR = PROJECT_ROOT / "monitoring" / "plots"

REPORT_DIR.mkdir(parents=True, exist_ok=True)
PLOT_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# 2. MLFLOW CONFIGURATION
# --------------------------------------------------

EXPERIMENT_NAME = "WasteWise_Expiry_Risk"

EXPECTED_METRICS = [
    "accuracy",
    "precision",
    "recall",
    "f1_score",
    "roc_auc",
    "pr_auc",
]


# --------------------------------------------------
# 3. CONNECT TO MLFLOW
# --------------------------------------------------

def connect_mlflow():

    print("\nConnecting to MLflow...")

    if not DATABASE_FILE.exists():
        raise FileNotFoundError(
            f"MLflow database not found: {DATABASE_FILE}"
        )

    tracking_uri = (
        f"sqlite:///{DATABASE_FILE.as_posix()}"
    )

    mlflow.set_tracking_uri(tracking_uri)

    client = MlflowClient()

    experiment = client.get_experiment_by_name(
        EXPERIMENT_NAME
    )

    if experiment is None:
        raise ValueError(
            f"Experiment not found: {EXPERIMENT_NAME}"
        )

    print("MLflow connected successfully!")
    print("Experiment:", experiment.name)

    return client, experiment


# --------------------------------------------------
# 4. LOAD MODEL PERFORMANCE METRICS
# --------------------------------------------------

def load_performance_metrics(client, experiment):

    print("\nLoading model evaluation metrics...")

    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        max_results=100,
        order_by=["attributes.start_time DESC"]
    )

    if not runs:
        raise ValueError(
            "No MLflow runs found."
        )

    # Select the Logistic Regression baseline run
    matching_runs = [
        run for run in runs
        if run.info.run_name == "Logistic_Regression_Baseline"
    ]

    if not matching_runs:
        raise ValueError(
            "Logistic Regression baseline run not found."
        )

    selected_run = matching_runs[0]

    metrics = selected_run.data.metrics

    missing_metrics = [
        metric for metric in EXPECTED_METRICS
        if metric not in metrics
    ]

    if missing_metrics:
        raise ValueError(
            f"Missing MLflow metrics: {missing_metrics}"
        )

    results = pd.DataFrame({
        "metric": EXPECTED_METRICS,
        "score": [
            metrics[metric]
            for metric in EXPECTED_METRICS
        ]
    })

    print("Run:", selected_run.info.run_name)
    print("Run ID:", selected_run.info.run_id)

    return results, selected_run


# --------------------------------------------------
# 5. DISPLAY PERFORMANCE
# --------------------------------------------------

def display_performance(results):

    print("\nModel Performance Results:")

    display_df = results.copy()

    display_df["score_percentage"] = (
        display_df["score"] * 100
    ).round(2)

    print(
        display_df.to_string(index=False)
    )


# --------------------------------------------------
# 6. SAVE PERFORMANCE REPORT
# --------------------------------------------------

def save_report(results, selected_run):

    report = results.copy()

    report["score_percentage"] = (
        report["score"] * 100
    )

    report["run_name"] = selected_run.info.run_name
    report["run_id"] = selected_run.info.run_id

    report["metric_source"] = (
        "Previously recorded test evaluation"
    )

    report_path = (
        REPORT_DIR / "model_performance_report.csv"
    )

    report.to_csv(
        report_path,
        index=False
    )

    print("\nPerformance report saved:")
    print(report_path)


# --------------------------------------------------
# 7. CREATE PERFORMANCE CHART
# --------------------------------------------------

def create_performance_chart(results):

    print("\nCreating performance chart...")

    plt.figure(figsize=(10, 6))

    plt.bar(
        results["metric"],
        results["score"] * 100
    )

    plt.title(
        "WasteWise AI - Model Performance"
    )

    plt.xlabel("Evaluation Metrics")
    plt.ylabel("Score (%)")

    plt.ylim(0, 100)

    plt.xticks(rotation=20, ha="right")

    plt.tight_layout()

    chart_path = (
        PLOT_DIR / "model_performance_overview.png"
    )

    plt.savefig(
        chart_path,
        dpi=150
    )

    plt.close()

    print("Performance chart saved:")
    print(chart_path)


# --------------------------------------------------
# 8. MAIN FUNCTION
# --------------------------------------------------

def main():

    print("=" * 60)
    print("WASTEWISE AI - MODEL PERFORMANCE MONITORING")
    print("=" * 60)

    client, experiment = connect_mlflow()

    results, selected_run = load_performance_metrics(
        client,
        experiment
    )

    display_performance(results)

    save_report(
        results,
        selected_run
    )

    create_performance_chart(results)

    print("\n" + "=" * 60)
    print("MODEL PERFORMANCE REPORT COMPLETED")
    print("=" * 60)

    print(
        "\nNote: These are historical test metrics, "
        "not live production measurements."
    )


if __name__ == "__main__":
    main()
