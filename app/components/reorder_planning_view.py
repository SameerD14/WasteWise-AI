import math
import pandas as pd
import plotly.express as px
import streamlit as st


GREEN = "#35C99A"
AMBER = "#F2B84B"
RED = "#EF6B68"
TEAL = "#35A995"
PANEL = "#192630"
TEXT = "#F1F5F7"


def show_reorder_planning(df):

    st.title("Reorder Planning")
    st.caption(
        "Identify products requiring replenishment using estimated "
        "daily demand and available inventory."
    )

    if df is None or df.empty:
        st.warning("No inventory records are available.")
        return

    required_columns = [
        "product_id",
        "product_name",
        "quantity_remaining",
        "avg_daily_sales_7d",
    ]

    missing = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing:
        st.error(
            "Required inventory columns are missing: "
            + ", ".join(missing)
        )
        return

    data = df.copy()

    data["quantity_remaining"] = pd.to_numeric(
        data["quantity_remaining"], errors="coerce"
    ).fillna(0).clip(lower=0)

    data["avg_daily_sales_7d"] = pd.to_numeric(
        data["avg_daily_sales_7d"], errors="coerce"
    )

    aggregations = {
        "product_name": ("product_name", "first"),
        "available_stock": ("quantity_remaining", "sum"),
        "daily_demand": ("avg_daily_sales_7d", "mean"),
    }

    if "category" in data.columns:
        aggregations["category"] = ("category", "first")

    if "unit_cost" in data.columns:
        data["unit_cost"] = pd.to_numeric(
            data["unit_cost"], errors="coerce"
        )
        aggregations["unit_cost"] = ("unit_cost", "mean")

    products = (
        data.groupby("product_id", as_index=False)
        .agg(**aggregations)
    )

    if "category" not in products.columns:
        products["category"] = "Uncategorized"

    if "unit_cost" not in products.columns:
        products["unit_cost"] = 0

    products["category"] = (
        products["category"].fillna("Uncategorized")
    )

    products["daily_demand"] = (
        products["daily_demand"].clip(lower=0)
    )

    # ======================================
    # REORDER SETTINGS
    # ======================================

    st.subheader("Reorder Settings")

    setting_col1, setting_col2 = st.columns(2)

    with setting_col1:
        target_days = st.selectbox(
            "Target Stock Coverage",
            options=[7, 14, 21, 30],
            index=1,
            format_func=lambda value: f"{value} days",
        )

    with setting_col2:
        st.metric(
            "Products Analysed",
            f"{len(products):,}",
        )

    # ======================================
    # PRODUCT-LEVEL CALCULATIONS
    # ======================================

    products["stock_coverage_days"] = (
        products["available_stock"]
        / products["daily_demand"].where(
            products["daily_demand"] > 0
        )
    )

    products["target_stock"] = (
        products["daily_demand"] * target_days
    )

    products["reorder_quantity"] = products.apply(
        lambda row: (
            math.ceil(
                max(
                    0,
                    row["target_stock"] - row["available_stock"]
                )
            )
            if pd.notna(row["daily_demand"])
            and row["daily_demand"] > 0
            else 0
        ),
        axis=1,
    )

    def get_priority(row):

        demand = row["daily_demand"]
        coverage = row["stock_coverage_days"]

        if pd.isna(demand) or demand <= 0:
            return "Review Data"

        if pd.isna(coverage):
            return "Review Data"

        if coverage <= 3:
            return "Critical"

        if coverage <= 7:
            return "High"

        if coverage <= 14:
            return "Medium"

        return "Normal"

    products["priority"] = products.apply(
        get_priority, axis=1
    )

    products["estimated_order_cost"] = (
        products["reorder_quantity"]
        * products["unit_cost"].fillna(0).clip(lower=0)
    )

    # ======================================
    # KPI OVERVIEW
    # ======================================

    st.divider()
    st.subheader("Replenishment Overview")

    critical_count = (
        products["priority"] == "Critical"
    ).sum()

    high_count = (
        products["priority"] == "High"
    ).sum()

    medium_count = (
        products["priority"] == "Medium"
    ).sum()

    reorder_count = (
        products["reorder_quantity"] > 0
    ).sum()

    total_reorder_units = products[
        "reorder_quantity"
    ].sum()

    total_estimated_cost = products[
        "estimated_order_cost"
    ].sum()

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Critical Products", f"{critical_count:,}")
    c2.metric("High Priority", f"{high_count:,}")
    c3.metric("Products to Reorder", f"{reorder_count:,}")
    c4.metric("Suggested Reorder Units", f"{total_reorder_units:,.0f}")

    c5, c6 = st.columns(2)

    c5.metric(
        "Estimated Reorder Cost",
        f"₹{total_estimated_cost:,.2f}",
    )

    c6.metric(
        "Target Coverage",
        f"{target_days} days",
    )

    st.info(
        "Reorder quantities are estimates: "
        "target stock = average daily demand × selected coverage days. "
        "Suggested reorder = target stock minus available stock, "
        "rounded up. Review supplier lead times and actual demand "
        "before placing an order."
    )

    st.divider()

    # ======================================
    # PRIORITY FILTER
    # ======================================

    st.subheader("Reorder Recommendations")

    priority_options = [
        "All Priorities",
        "Critical",
        "High",
        "Medium",
        "Normal",
        "Review Data",
    ]

    selected_priority = st.selectbox(
        "Filter by Reorder Priority",
        priority_options,
    )

    filtered = products.copy()

    if selected_priority != "All Priorities":
        filtered = filtered[
            filtered["priority"] == selected_priority
        ]

    # ======================================
    # REORDER TABLE
    # ======================================

    display_columns = [
        "product_name",
        "category",
        "available_stock",
        "daily_demand",
        "stock_coverage_days",
        "target_stock",
        "reorder_quantity",
        "priority",
        "estimated_order_cost",
    ]

    st.dataframe(
        filtered[display_columns].sort_values(
            "reorder_quantity", ascending=False
        ),
        use_container_width=True,
        hide_index=True,
        height=430,
        column_config={
            "product_name": st.column_config.TextColumn(
                "Product"
            ),
            "category": st.column_config.TextColumn(
                "Category"
            ),
            "available_stock": st.column_config.NumberColumn(
                "Available Stock",
                format="%,.0f",
            ),
            "daily_demand": st.column_config.NumberColumn(
                "Avg Daily Demand",
                format="%,.2f",
            ),
            "stock_coverage_days": st.column_config.NumberColumn(
                "Stock Coverage",
                format="%.1f days",
            ),
            "target_stock": st.column_config.NumberColumn(
                f"Target Stock ({target_days} days)",
                format="%,.1f",
            ),
            "reorder_quantity": st.column_config.NumberColumn(
                "Suggested Reorder",
                format="%,.0f",
            ),
            "priority": st.column_config.TextColumn(
                "Priority"
            ),
            "estimated_order_cost": st.column_config.NumberColumn(
                "Estimated Cost",
                format="₹ %,.2f",
            ),
        },
    )

    st.divider()

    # ======================================
    # REORDER QUANTITY CHART
    # ======================================

    st.subheader("Products Requiring Replenishment")

    chart_data = products[
        products["reorder_quantity"] > 0
    ].sort_values(
        "reorder_quantity", ascending=True
    ).tail(10)

    if not chart_data.empty:

        fig = px.bar(
            chart_data,
            x="reorder_quantity",
            y="product_name",
            orientation="h",
            text="reorder_quantity",
            color="priority",
            color_discrete_map={
                "Critical": RED,
                "High": AMBER,
                "Medium": TEAL,
                "Normal": GREEN,
            },
            title="Top 10 Suggested Reorder Quantities",
        )

        fig.update_traces(
            texttemplate="%{x:,.0f}",
            textposition="outside",
            cliponaxis=False,
        )

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor=PANEL,
            plot_bgcolor=PANEL,
            font=dict(color=TEXT, size=13),
            height=430,
            margin=dict(l=30, r=60, t=65, b=45),
            xaxis_title="Suggested Reorder Units",
            yaxis_title="Product",
            legend_title="Priority",
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False},
        )

    else:
        st.success(
            f"No additional stock is required to meet the "
            f"selected {target_days}-day target based on current estimates."
        )

    # ======================================
    # EXPORT REPORT
    # ======================================

    st.divider()
    st.subheader("Export Reorder Report")

    csv_data = products.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        "Download Reorder Planning CSV",
        data=csv_data,
        file_name="wastewise_reorder_plan.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.caption(
        "WasteWise AI | Reorder estimates use product-level "
        "average daily sales and current inventory. "
        "This page does not create purchase orders."
    )
