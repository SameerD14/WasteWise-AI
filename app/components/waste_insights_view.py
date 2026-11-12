import pandas as pd
import plotly.express as px
import streamlit as st


def show_waste_insights(df):

    st.title("Waste Insights")
    st.caption(
        "Analyze expired stock, inventory surplus and potential "
        "financial exposure."
    )

    if df is None or df.empty:
        st.warning("No inventory data is available.")
        return

    required = [
        "batch_id",
        "product_name",
        "risk_status",
        "quantity_remaining",
        "unit_cost",
    ]

    missing = [column for column in required if column not in df.columns]

    if missing:
        st.error("Missing required columns: " + ", ".join(missing))
        return

    data = df.copy()

    numeric_columns = [
        "batch_id",
        "quantity_remaining",
        "initial_quantity",
        "unit_cost",
        "days_to_expiry",
        "inventory_surplus",
    ]

    for column in numeric_columns:
        if column in data.columns:
            data[column] = pd.to_numeric(
                data[column], errors="coerce"
            )

    data["quantity_remaining"] = data["quantity_remaining"].fillna(0)
    data["unit_cost"] = data["unit_cost"].fillna(0)
    data["risk_status"] = data["risk_status"].fillna("Data Incomplete")

    # Positive surplus only. Negative surplus is not waste.
    if "inventory_surplus" in data.columns:
        data["positive_surplus"] = (
            data["inventory_surplus"].clip(lower=0).fillna(0)
        )
    else:
        data["positive_surplus"] = 0

    data["expired_units"] = 0.0
    data.loc[
        data["risk_status"] == "Expired", "expired_units"
    ] = data["quantity_remaining"]

    data["expired_stock_value"] = (
        data["expired_units"] * data["unit_cost"]
    )

    # Do not count expired stock surplus a second time.
    non_expired = data["risk_status"] != "Expired"

    data["non_expired_surplus_value"] = (
        data["positive_surplus"].where(non_expired, 0)
        * data["unit_cost"]
    )

    data["potential_exposure_value"] = (
        data["expired_stock_value"]
        + data["non_expired_surplus_value"]
    )

    data["surplus_value"] = data["non_expired_surplus_value"]

    # ======================================
    # FILTERS
    # ======================================

    st.subheader("Waste Analysis Filters")

    f1, f2 = st.columns(2)

    with f1:
        products = [
            "All",
            *sorted(data["product_name"].dropna().unique().tolist()),
        ]
        selected_product = st.selectbox("Product", products)

    with f2:
        risk_options = [
            "All",
            *sorted(data["risk_status"].dropna().unique().tolist()),
        ]
        selected_risk = st.selectbox("Risk Status", risk_options)

    filtered = data.copy()

    if selected_product != "All":
        filtered = filtered[
            filtered["product_name"] == selected_product
        ]

    if selected_risk != "All":
        filtered = filtered[
            filtered["risk_status"] == selected_risk
        ]

    # ======================================
    # KPI CARDS
    # ======================================

    expired = filtered[
        filtered["risk_status"] == "Expired"
    ]

    expiring_soon = filtered[
        filtered["days_to_expiry"].between(0, 7, inclusive="both")
    ] if "days_to_expiry" in filtered.columns else filtered.iloc[0:0]

    non_expired_filtered = filtered[
        filtered["risk_status"] != "Expired"
    ]

    surplus_units = non_expired_filtered["positive_surplus"].sum()
    expired_units = filtered["expired_units"].sum()
    expired_value = filtered["expired_stock_value"].sum()
    surplus_value = filtered["surplus_value"].sum()

    st.subheader("Waste Exposure Overview")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Expired Batches", f"{len(expired):,}")
    c2.metric("Expired Stock Units", f"{expired_units:,.0f}")
    c3.metric("Surplus Units", f"{surplus_units:,.0f}")
    c4.metric(
        "Expiring Within 7 Days",
        f"{len(expiring_soon):,}",
    )

    c5, c6 = st.columns(2)

    c5.metric("Estimated Expired Stock Value", f"₹{expired_value:,.2f}")
    c6.metric("Estimated Surplus Stock Value", f"₹{surplus_value:,.2f}")

    st.info(
        "Financial values are estimates using remaining quantity or "
        "positive inventory surplus multiplied by unit cost. They do "
        "not represent confirmed waste, disposal or realized losses."
    )

    st.divider()

    # ======================================
    # RISK DISTRIBUTION
    # ======================================

    st.subheader("Inventory Risk Distribution")

    risk_counts = (
        filtered["risk_status"]
        .value_counts()
        .rename_axis("Risk Status")
        .reset_index(name="Batches")
    )

    if not risk_counts.empty:
        fig_risk = px.pie(
            risk_counts,
            names="Risk Status",
            values="Batches",
            hole=0.55,
            title="Batches by Risk Status",
        )

        fig_risk.update_layout(
            template="plotly_dark",
            height=380,
            margin=dict(t=55, b=25, l=20, r=20),
        )

        st.plotly_chart(
            fig_risk,
            use_container_width=True,
            config={"displayModeBar": False},
        )

    st.divider()

    # ======================================
    # PRODUCT-WISE EXPOSURE
    # ======================================

    st.subheader("Product-wise Waste Exposure")

    product_summary = (
        filtered.groupby("product_name", as_index=False)
        .agg(
            expired_units=("expired_units", "sum"),
            surplus_units=("positive_surplus", "sum"),
            expired_value=("expired_stock_value", "sum"),
            surplus_value=("surplus_value", "sum"),
        )
    )

    product_summary["estimated_exposure"] = (
        product_summary["expired_value"]
        + product_summary["surplus_value"]
    )

    product_summary = product_summary.sort_values(
        "estimated_exposure", ascending=False
    )

    fig_product = px.bar(
        product_summary.head(10),
        x="product_name",
        y="estimated_exposure",
        color="estimated_exposure",
        text_auto=".2s",
        title="Top 10 Products by Estimated Exposure",
        labels={
            "product_name": "Product",
            "estimated_exposure": "Estimated Value (₹)",
        },
    )

    fig_product.update_layout(
        template="plotly_dark",
        height=430,
        xaxis_tickangle=-30,
        showlegend=False,
    )

    st.plotly_chart(
        fig_product,
        use_container_width=True,
        config={"displayModeBar": False},
    )

    # ======================================
    # CATEGORY-WISE EXPOSURE
    # ======================================

    if "category" in filtered.columns:

        st.subheader("Category-wise Exposure")

        category_summary = (
            filtered.groupby("category", as_index=False)
            .agg(
                expired_value=("expired_stock_value", "sum"),
                surplus_value=("surplus_value", "sum"),
            )
        )

        category_summary["estimated_exposure"] = (
            category_summary["expired_value"]
            + category_summary["surplus_value"]
        )

        fig_category = px.bar(
            category_summary,
            x="category",
            y="estimated_exposure",
            color="category",
            text_auto=".2s",
            title="Estimated Exposure by Category",
            labels={
                "category": "Category",
                "estimated_exposure": "Estimated Value (₹)",
            },
        )

        fig_category.update_layout(
            template="plotly_dark",
            height=380,
            showlegend=False,
        )

        st.plotly_chart(
            fig_category,
            use_container_width=True,
            config={"displayModeBar": False},
        )

    st.divider()

    # ======================================
    # ATTENTION TABLE
    # ======================================

    st.subheader("Inventory Requiring Attention")

    attention = filtered[
        (filtered["risk_status"] == "Expired")
        | (filtered["days_to_expiry"].between(0, 7))
        | (filtered["positive_surplus"] > 0)
    ].copy()

    attention_columns = [
        "batch_id",
        "product_name",
        "risk_status",
        "days_to_expiry",
        "quantity_remaining",
        "positive_surplus",
        "unit_cost",
        "potential_exposure_value",
    ]

    attention_columns = [
        column for column in attention_columns
        if column in attention.columns
    ]

    attention = attention[attention_columns].sort_values(
        "potential_exposure_value",
        ascending=False,
    )

    st.dataframe(
        attention,
        use_container_width=True,
        hide_index=True,
        height=420,
        column_config={
            "batch_id": st.column_config.NumberColumn(
                "Batch ID", format="%d"
            ),
            "days_to_expiry": st.column_config.NumberColumn(
                "Days to Expiry", format="%.0f"
            ),
            "quantity_remaining": st.column_config.NumberColumn(
                "Remaining Units", format="%,.0f"
            ),
            "positive_surplus": st.column_config.NumberColumn(
                "Positive Surplus", format="%,.1f"
            ),
            "unit_cost": st.column_config.NumberColumn(
                "Unit Cost", format="₹%.2f"
            ),
            "potential_exposure_value": st.column_config.NumberColumn(
                "Estimated Exposure (₹)", format="₹%,.2f"
            ),
        },
    )

    # ======================================
    # CSV EXPORT
    # ======================================

    st.subheader("Export Waste Insights")

    csv_data = filtered.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download Waste Insights CSV",
        data=csv_data,
        file_name="wastewise_waste_insights.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.caption(
        "This module analyzes inventory exposure using existing "
        "inventory records. It does not measure actual discarded food."
    )
