
"""
WasteWise AI - Data Drift Monitoring

Compares:
    Baseline: July 1 to October 7, 2026
    Current:  October 8 to November 3, 2026

This is an exploratory comparison using historical project data.
It is not a live production monitoring system.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import ks_2samp


# --------------------------------------------------
# 1. PROJECT PATHS
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = PROJECT_ROOT / "data" / "processed" / "inventory_features.csv"

REPORT_DIR = PROJECT_ROOT / "monitoring" / "reports"
PLOT_DIR = PROJECT_ROOT / "monitoring" / "plots"

REPORT_DIR.mkdir(parents=True, exist_ok=True)
PLOT_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# 2. MONITORING SETTINGS
# --------------------------------------------------

CUTOFF_DATE = pd.Timestamp("2026-10-07")

FEATURES = [
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
    "gross_margin_pct",
]


# --------------------------------------------------
# 3. POPULATION STABILITY INDEX (PSI)
# --------------------------------------------------

def calculate_psi(baseline, current):
    """
    Measures how much a feature distribution changes.

    PSI below 0.10: Low change
    PSI 0.10 to 0.20: Moderate change
    PSI 0.20 or above: High change
    """

    baseline = np.asarray(baseline, dtype=float)
    current = np.asarray(current, dtype=float)

    # Create bins using baseline data
    bins = np.unique(
        np.quantile(baseline, np.linspace(0, 1, 11))
    )

    # Handle features with constant values
    if len(bins) < 2:
        return 0.0

    bins[0] = -np.inf
    bins[-1] = np.inf

    baseline_counts, _ = np.histogram(baseline, bins=bins)
    current_counts, _ = np.histogram(current, bins=bins)

    # Convert counts into proportions
    baseline_pct = baseline_counts / len(baseline)
    current_pct = current_counts / len(current)

    # Avoid division by zero
    epsilon = 0.000001

    baseline_pct = np.clip(baseline_pct, epsilon, None)
    current_pct = np.clip(current_pct, epsilon, None)

    psi = np.sum(
        (current_pct - baseline_pct)
        * np.log(current_pct / baseline_pct)
    )

    return float(psi)


# --------------------------------------------------
# 4. LOAD DATA
# --------------------------------------------------

def load_data():

    print("\nLoading inventory feature dataset...")

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_PATH}"
        )

    df = pd.read_csv(DATA_PATH)

    required_columns = FEATURES + ["snapshot_date"]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    df["snapshot_date"] = pd.to_datetime(
        df["snapshot_date"],
        errors="coerce"
    )

    df = df.dropna(subset=["snapshot_date"])

    print("Dataset loaded successfully!")
    print("Total records:", len(df))

    return df


# --------------------------------------------------
# 5. SPLIT BASELINE AND CURRENT DATA
# --------------------------------------------------

def split_data(df):

    baseline = df[
        df["snapshot_date"] <= CUTOFF_DATE
    ].copy()

    current = df[
        df["snapshot_date"] > CUTOFF_DATE
    ].copy()

    print("\nData split completed")
    print("Baseline records:", len(baseline))
    print("Current records:", len(current))

    if len(baseline) == 0 or len(current) == 0:
        raise ValueError(
            "Baseline or current dataset is empty."
        )

    if len(current) < 100:
        print(
            "WARNING: Current dataset has fewer than "
            "100 records. Interpret results cautiously."
        )

    return baseline, current


# --------------------------------------------------
# 6. CHECK DATA DRIFT
# --------------------------------------------------

def monitor_drift(baseline, current):

    results = []

    print("\nChecking feature drift...")

    for feature in FEATURES:

        baseline_values = pd.to_numeric(
            baseline[feature],
            errors="coerce"
        ).replace([np.inf, -np.inf], np.nan).dropna()

        current_values = pd.to_numeric(
            current[feature],
            errors="coerce"
        ).replace([np.inf, -np.inf], np.nan).dropna()

        if len(baseline_values) < 2 or len(current_values) < 2:

            print(f"Skipping {feature}: insufficient numeric data")

            continue

        # Statistical comparison
        ks_statistic, ks_p_value = ks_2samp(
            baseline_values,
            current_values
        )

        # Distribution change measurement
        psi_score = calculate_psi(
            baseline_values,
            current_values
        )

        # Interpret PSI
        if psi_score >= 0.20:
            status = "HIGH DRIFT"

        elif psi_score >= 0.10:
            status = "MODERATE DRIFT"

        else:
            status = "LOW DRIFT"

        results.append({
            "feature": feature,
            "baseline_count": len(baseline_values),
            "current_count": len(current_values),
            "baseline_mean": baseline_values.mean(),
            "current_mean": current_values.mean(),
            "ks_statistic": ks_statistic,
            "ks_p_value": ks_p_value,
            "psi_score": psi_score,
            "drift_status": status,
        })

        print(
            f"{feature}: PSI={psi_score:.4f} | {status}"
        )

    return pd.DataFrame(results)


# --------------------------------------------------
# 7. SAVE MONITORING REPORT
# --------------------------------------------------

def save_report(results):

    report_path = REPORT_DIR / "data_drift_report.csv"

    results.to_csv(report_path, index=False)

    print("\nMonitoring report saved:")
    print(report_path)


# --------------------------------------------------
# 8. CREATE DRIFT CHART
# --------------------------------------------------

def create_drift_chart(results):

    if results.empty:
        print("No results available for plotting.")
        return

    plt.figure(figsize=(12, 7))

    plt.barh(
        results["feature"],
        results["psi_score"]
    )

    plt.axvline(
        0.10,
        linestyle="--",
        label="Moderate drift threshold"
    )

    plt.axvline(
        0.20,
        linestyle="--",
        label="High drift threshold"
    )

    plt.xlabel("Population Stability Index (PSI)")
    plt.ylabel("Inventory Features")
    plt.title("WasteWise AI - Feature Data Drift Monitoring")

    plt.legend()
    plt.tight_layout()

    plot_path = PLOT_DIR / "data_drift_overview.png"

    plt.savefig(plot_path, dpi=150)
    plt.close()

    print("\nDrift chart saved:")
    print(plot_path)


# --------------------------------------------------
# 9. MAIN FUNCTION
# --------------------------------------------------

def main():

    print("=" * 60)
    print("WASTEWISE AI - DATA DRIFT MONITORING")
    print("=" * 60)

    df = load_data()

    baseline, current = split_data(df)

    results = monitor_drift(
        baseline,
        current
    )

    if results.empty:
        raise ValueError("No features could be monitored.")

    save_report(results)

    create_drift_chart(results)

    print("\n" + "=" * 60)
    print("DATA DRIFT MONITORING COMPLETED")
    print("=" * 60)

    print("\nDrift Summary:")
    print(
        results[
            ["feature", "psi_score", "drift_status"]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
