import pandas as pd
import plotly.express as px
import streamlit as st

PANEL = "#192630"
TEXT = "#F1F5F7"
GREEN = "#35C99A"
AMBER = "#F2B84B"
RED = "#EF6B68"
TEAL = "#35A995"


def show_recommendations(df):

    st.title("Inventory Recommendations")
    st.caption(
        "Review ML-based expiry risk, inventory priorities "
        "and recommended actions."
    )

    if df is None or df.empty:
        st.warning("No inventory records are available.")
        return

    required = [
        "batch_id",
        "product_name",
        "risk_status",
        "priority",
        "recommended_action",
    ]

    missing = [c for c in required if c not in df.columns]

    if missing:
        st.error("Missing columns: " + ", ".join(missing))
        return

    data = df.copy()

    # Numeric cleanup
    numeric_columns = [
        "batch_id",
        "days_to_expiry",
        "quantity_remaining",
        "inventory_surplus",
        "risk_probability",
    ]

    for column in numeric_columns:
        if column in data.columns:
            data[column] = pd.to_numeric(
                data[column], errors="coerce"
            )

    data["risk_status"] = (
        data["risk_status"].fillna("Data Incomplete")
    )

    data["priority"] = (
        data["priority"].fillna("Review")
    )

    data["recommended_action"] = (
        data["recommended_action"].fillna(
            "Review inventory information."
        )
    )

    # ======================================
    # KPI OVERVIEW
    # ======================================

    st.subheader("Recommendation Overview")

    critical = data[
        data["priority"].str.lower() == "critical"
    ]

    high = data[
        data["priority"].str.lower() == "high"
    ]

    review = data[
        data["priority"].str.lower() == "review"
    ]

    normal = data[
        data["priority"].str.lower() == "normal"
    ]

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Critical Batches", f"{len(critical):,}")
    c2.metric("High Priority", f"{len(high):,}")
    c3.metric("Review Required", f"{len(review):,}")
    c4.metric("Normal Batches", f"{len(normal):,}")

    st.divider()

    # ======================================
    # FILTERS
    # ======================================

    st.subheader("Filter Recommendations")

    f1, f2, f3 = st.columns(3)

    priority_options = [
        "All",
        "Critical",
        "High",
        "Review",
        "Normal",
    ]

    risk_options = [
        "All",
        *sorted(data["risk_status"].dropna().unique().tolist()),
    ]

    with f1:
        selected_priority = st.selectbox(
            "Priority",
            priority_options,
        )

    with f2:
        selected_risk = st.selectbox(
            "Expiry Risk",
            risk_options,
        )

    with f3:
        product_options = [
            "All",
            *sorted(data["product_name"].dropna().unique().tolist()),
        ]

        selected_product = st.selectbox(
            "Product",
            product_options,
        )

    filtered = data.copy()

    if selected_priority != "All":
        filtered = filtered[
            filtered["priority"].str.lower()
            == selected_priority.lower()
        ]

    if selected_risk != "All":
        filtered = filtered[
            filtered["risk_status"] == selected_risk
        ]

    if selected_product != "All":
        filtered = filtered[
            filtered["product_name"] == selected_product
        ]

    st.caption(
        f"Showing {len(filtered):,} of {len(data):,} inventory batches."
    )

    # ======================================
    # PRIORITY DISTRIBUTION
    # ======================================

    st.subheader("Priority Distribution")

    priority_order = [
        "Critical",
        "High",
        "Review",
        "Normal",
    ]

    priority_data = (
        data["priority"]
        .value_counts()
        .reindex(priority_order, fill_value=0)
        .rename_axis("Priority")
        .reset_index(name="Batches")
    )

    fig_priority = px.bar(
        priority_data,
        x="Priority",
        y="Batches",
        color="Priority",
        text="Batches",
        color_discrete_map={
            "Critical": RED,
            "High": AMBER,
            "Review": TEAL,
            "Normal": GREEN,
        },
        title="Inventory Recommendation Priorities",
    )

    fig_priority.update_traces(
        textposition="outside",
        cliponaxis=False,
    )

    fig_priority.update_layout(
        template="plotly_dark",
        paper_bgcolor=PANEL,
        plot_bgcolor=PANEL,
        font=dict(color=TEXT, size=13),
        height=370,
        showlegend=False,
    )

    st.plotly_chart(
        fig_priority,
        use_container_width=True,
        config={"displayModeBar": False},
    )

    st.divider()

    # ======================================
    # RECOMMENDATION TABLE
    # ======================================

    st.subheader("Recommended Inventory Actions")

    display_columns = [
        "batch_id",
        "product_name",
        "risk_status",
        "priority",
    ]

    optional_columns = [
        "days_to_expiry",
        "quantity_remaining",
        "inventory_surplus",
        "risk_probability",
        "recommended_action",
    ]

    for column in optional_columns:
        if column in filtered.columns:
            display_columns.append(column)

    display = filtered[display_columns].copy()

    rename_columns = {
        "batch_id": "Batch ID",
        "product_name": "Product",
        "risk_status": "Expiry Risk",
        "priority": "Priority",
        "days_to_expiry": "Days to Expiry",
        "quantity_remaining": "Remaining Stock",
        "inventory_surplus": "Inventory Surplus",
        "risk_probability": "Risk Probability (%)",
        "recommended_action": "Recommended Action",
    }

    display = display.rename(columns=rename_columns)

    column_config = {
        "Batch ID": st.column_config.NumberColumn(
            "Batch ID",
            format="%d",
        ),
        "Product": st.column_config.TextColumn("Product"),
        "Expiry Risk": st.column_config.TextColumn("Expiry Risk"),
        "Priority": st.column_config.TextColumn("Priority"),
        "Days to Expiry": st.column_config.NumberColumn(
            "Days to Expiry",
            format="%.0f",
        ),
        "Remaining Stock": st.column_config.NumberColumn(
            "Remaining Stock",
            format="%,.0f",
        ),
        "Inventory Surplus": st.column_config.NumberColumn(
            "Inventory Surplus",
            format="%,.1f",
        ),
        "Risk Probability (%)": st.column_config.NumberColumn(
            "Risk Probability (%)",
            format="%.2f",
        ),
        "Recommended Action": st.column_config.TextColumn(
            "Recommended Action",
            width="large",
        ),
    }

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        height=500,
        column_config=column_config,
    )

    # ======================================
    # ACTION SUMMARY
    # ======================================

    st.divider()
    st.subheader("Priority Action Summary")

    if not critical.empty:
        st.error(
            f"{len(critical):,} critical batches need immediate "
            "review. Check expired and expiring-today stock first."
        )

    if not high.empty:
        st.warning(
            f"{len(high):,} high-priority batches need closer "
            "monitoring and inventory review."
        )

    if not review.empty:
        st.info(
            f"{len(review):,} batches require additional data "
            "or inventory surplus review."
        )

    if critical.empty and high.empty and review.empty:
        st.success(
            "No critical, high-priority or review-required "
            "recommendations were found."
        )

    # ======================================
    # EXPORT
    # ======================================

    st.divider()
    st.subheader("Export Recommendations")

    csv_data = filtered.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        "Download Recommendations CSV",
        data=csv_data,
        file_name="wastewise_inventory_recommendations.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.caption(
        "Recommendations are based on stored inventory records "
        "and existing ML predictions. Critical food-safety decisions "
        "must follow applicable food-safety procedures."
    )
