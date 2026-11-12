
"""
WasteWise AI - Monitoring Dashboard

Displays:
1. Prediction Monitoring
2. Prediction Data Quality
3. Data Drift Monitoring
4. Model Performance Monitoring
5. Downloadable Reports

All results are based on historical project reports.
This is not a live production monitoring system.
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# --------------------------------------------------
# 1. PROJECT PATHS
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

REPORT_DIR = PROJECT_ROOT / "monitoring" / "reports"


# --------------------------------------------------
# 3. LOAD REPORTS
# --------------------------------------------------

def load_report(filename):

    file_path = REPORT_DIR / filename

    if not file_path.exists():
        return None

    return pd.read_csv(file_path)


def show_model_monitoring():

    # --------------------------------------------------
    # 4. DASHBOARD HEADER
    # --------------------------------------------------

    st.title("📊 WasteWise AI - Monitoring Dashboard")

    st.markdown(
        """
        Monitor inventory data drift, model predictions,
        and historical model evaluation performance.
        """
    )

    st.info(
        "This dashboard displays historical project reports. "
        "It is not a live production monitoring system."
    )

    if st.button("🔄 Refresh Dashboard"):
        st.rerun()


    # --------------------------------------------------
    # 5. LOAD REPORTS
    # --------------------------------------------------

    drift_df = load_report("data_drift_report.csv")

    prediction_df = load_report(
        "prediction_status_summary.csv"
    )

    quality_df = load_report(
        "prediction_data_quality.csv"
    )

    probability_df = load_report(
        "risk_probability_summary.csv"
    )

    performance_df = load_report(
        "model_performance_report.csv"
    )


    # --------------------------------------------------
    # 6. PREDICTION MONITORING
    # --------------------------------------------------

    st.header("1. Prediction Monitoring")

    if prediction_df is not None and not prediction_df.empty:

        counts = dict(
            zip(
                prediction_df["risk_status"],
                prediction_df["batch_count"]
            )
        )

        total_predictions = int(
            prediction_df["batch_count"].sum()
        )

        high_risk = int(counts.get("High Risk", 0))
        low_risk = int(counts.get("Low Risk", 0))
        expired = int(counts.get("Expired", 0))

        expires_today = int(
            counts.get(
                "Expires Today - Immediate Review",
                0
            )
        )

        col1, col2, col3, col4, col5 = st.columns(5)

        col1.metric("Total Batches", f"{total_predictions:,}")
        col2.metric("High Risk", f"{high_risk:,}")
        col3.metric("Low Risk", f"{low_risk:,}")
        col4.metric("Expired", f"{expired:,}")
        col5.metric("Expires Today", f"{expires_today:,}")

        st.subheader("Prediction Distribution")

        prediction_chart = px.bar(
            prediction_df,
            x="risk_status",
            y="batch_count",
            text="batch_count",
            title="Inventory Risk Distribution"
        )

        prediction_chart.update_layout(
            xaxis_title="Prediction Status",
            yaxis_title="Number of Batches",
            showlegend=False
        )

        st.plotly_chart(
            prediction_chart,
            width="stretch"
        )

        st.dataframe(
            prediction_df,
            width="stretch",
            hide_index=True
        )

    else:
        st.warning(
            "Prediction report not found. Run prediction_monitor.py."
        )


    # --------------------------------------------------
    # 7. RISK PROBABILITY MONITORING
    # --------------------------------------------------

    st.subheader("Risk Probability Summary")

    if probability_df is not None:

        probability_values = dict(
            zip(
                probability_df["metric"],
                probability_df["value"]
            )
        )

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Average Risk Probability",
            f"{probability_values.get('Average risk probability', 0):.2f}%"
        )

        col2.metric(
            "Median Risk Probability",
            f"{probability_values.get('Median risk probability', 0):.2f}%"
        )

        col3.metric(
            "Valid Probabilities",
            f"{int(probability_values.get('Valid risk probabilities', 0)):,}"
        )

    else:
        st.warning("Risk probability report not found.")


    # --------------------------------------------------
    # 8. PREDICTION DATA QUALITY
    # --------------------------------------------------

    st.header("2. Prediction Data Quality")

    if quality_df is not None:

        st.dataframe(
            quality_df,
            width="stretch",
            hide_index=True
        )

    else:
        st.warning("Prediction quality report not found.")


    # --------------------------------------------------
    # 9. DATA DRIFT MONITORING
    # --------------------------------------------------

    st.header("3. Data Drift Monitoring")

    if drift_df is not None and not drift_df.empty:

        high_drift = int(
            (drift_df["drift_status"] == "HIGH DRIFT").sum()
        )

        moderate_drift = int(
            (drift_df["drift_status"] == "MODERATE DRIFT").sum()
        )

        low_drift = int(
            (drift_df["drift_status"] == "LOW DRIFT").sum()
        )

        col1, col2, col3 = st.columns(3)

        col1.metric("High Drift Features", high_drift)
        col2.metric("Moderate Drift Features", moderate_drift)
        col3.metric("Low Drift Features", low_drift)

        st.subheader("Feature Drift Scores")

        drift_chart = px.bar(
            drift_df.sort_values("psi_score", ascending=False),
            x="feature",
            y="psi_score",
            color="drift_status",
            title="Population Stability Index (PSI)",
            text="psi_score"
        )

        drift_chart.update_layout(
            xaxis_title="Inventory Features",
            yaxis_title="PSI Score"
        )

        drift_chart.update_traces(
            texttemplate="%{text:.3f}",
            textposition="outside"
        )

        st.plotly_chart(
            drift_chart,
            width="stretch"
        )

        st.subheader("Drift Details")

        st.dataframe(
            drift_df,
            width="stretch",
            hide_index=True
        )

    else:
        st.warning(
            "Data drift report not found. Run drift_monitor.py."
        )


    # --------------------------------------------------
    # 10. MODEL PERFORMANCE MONITORING
    # --------------------------------------------------

    st.header("4. Model Performance Monitoring")

    if performance_df is not None and not performance_df.empty:

        st.caption(
            "Historical test evaluation metrics retrieved from MLflow."
        )

        # Display six performance metrics
        for start in range(0, len(performance_df), 3):

            columns = st.columns(3)

            for column, (_, row) in zip(
                columns,
                performance_df.iloc[start:start + 3].iterrows()
            ):

                column.metric(
                    row["metric"].replace("_", " ").title(),
                    f"{row['score_percentage']:.2f}%"
                )

        # Create interactive Plotly chart
        st.subheader("Model Performance Metrics")

        performance_chart = px.bar(
            performance_df,
            x="metric",
            y="score_percentage",
            text="score_percentage",
            title="Logistic Regression - Model Evaluation"
        )

        performance_chart.update_yaxes(
            title="Score (%)",
            range=[0, 100],
            ticksuffix="%"
        )

        performance_chart.update_xaxes(
            title="Evaluation Metrics"
        )

        performance_chart.update_traces(
            texttemplate="%{text:.2f}%",
            textposition="outside",
            cliponaxis=False
        )

        performance_chart.update_layout(
            showlegend=False,
            margin=dict(t=70, b=60)
        )

        st.plotly_chart(
            performance_chart,
            width="stretch"
        )

    else:
        st.warning(
            "Performance report not found. "
            "Run performance_monitor.py."
        )


    # --------------------------------------------------
    # 11. DOWNLOAD MONITORING REPORTS
    # --------------------------------------------------

    st.header("5. Download Monitoring Reports")

    report_files = [
        "data_drift_report.csv",
        "prediction_data_quality.csv",
        "prediction_status_summary.csv",
        "risk_probability_summary.csv",
        "risk_probability_by_status.csv",
        "model_performance_report.csv",
    ]

    available_reports = [
        filename
        for filename in report_files
        if (REPORT_DIR / filename).exists()
    ]

    if available_reports:

        for filename in available_reports:

            file_path = REPORT_DIR / filename

            with open(file_path, "rb") as file:

                st.download_button(
                    label=f"Download {filename}",
                    data=file.read(),
                    file_name=filename,
                    mime="text/csv",
                    key=filename
                )

    else:
        st.warning("No monitoring reports available.")


    # --------------------------------------------------
    # 12. FOOTER
    # --------------------------------------------------

    st.divider()

    st.caption(
        "WasteWise AI | Inventory Expiry Risk Monitoring | "
        "Historical and simulated project data"
    )
