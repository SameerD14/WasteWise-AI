import streamlit as st
import pandas as pd
import plotly.express as px


BG = "#101820"
PANEL = "#192630"
GREEN = "#16A879"
GREEN_LIGHT = "#35C99A"
TEAL = "#35A995"
AMBER = "#F2B84B"
RED = "#EF6B68"
TEXT = "#F1F5F7"
MUTED = "#A6B5BF"


def show_sales_analytics(df):

    st.title("Sales & Demand Analytics")
    st.caption(
        "Explore estimated product demand, inventory coverage "
        "and potential sales value."
    )

    if df is None or df.empty:
        st.warning("No inventory data is available.")
        return

    required = [
        "product_id",
        "product_name",
        "quantity_remaining",
        "avg_daily_sales_7d",
        "unit_price",
    ]

    missing = [column for column in required if column not in df.columns]

    if missing:
        st.error(
            "Required data is missing: " + ", ".join(missing)
        )
        return

    data = df.copy()

    for column in [
        "quantity_remaining",
        "avg_daily_sales_7d",
        "unit_price",
    ]:
        data[column] = pd.to_numeric(
            data[column], errors="coerce"
        )

    data["quantity_remaining"] = (
        data["quantity_remaining"].fillna(0).clip(lower=0)
    )

    # Use the average daily sales estimate per product.
    # Do not sum repeated batch-level averages.
    aggregations = {
        "product_name": ("product_name", "first"),
        "daily_demand": ("avg_daily_sales_7d", "mean"),
        "available_stock": ("quantity_remaining", "sum"),
        "unit_price": ("unit_price", "mean"),
    }

    if "category" in data.columns:
        aggregations["category"] = ("category", "first")

    products = (
        data.groupby("product_id", as_index=False)
        .agg(**aggregations)
    )

    products["daily_demand"] = (
        products["daily_demand"].clip(lower=0)
    )

    products["unit_price"] = (
        products["unit_price"].clip(lower=0)
    )

    products["category"] = (
        products["category"].fillna("Uncategorized")
        if "category" in products.columns
        else "Uncategorized"
    )

    products["estimated_daily_value"] = (
        products["daily_demand"] * products["unit_price"]
    )

    products["stock_coverage_days"] = (
        products["available_stock"]
        / products["daily_demand"].where(products["daily_demand"] > 0)
    )

    if products["daily_demand"].notna().sum() == 0:
        st.warning(
            "Average daily sales data is not available. "
            "Sales estimates cannot be calculated yet."
        )
        return

    if products["daily_demand"].fillna(0).sum() <= 0:
        st.warning(
            "No positive average daily demand values were found."
        )
        return

    # ======================================
    # ESTIMATION PERIOD
    # ======================================

    st.subheader("Estimate Period")

    period = st.selectbox(
        "Select demand estimation period",
        options=[7, 15, 30],
        format_func=lambda value: f"Next {value} days",
        index=0,
    )

    products["estimated_units"] = (
        products["daily_demand"] * period
    )

    products["estimated_value"] = (
        products["estimated_units"] * products["unit_price"]
    )

    total_daily_demand = products["daily_demand"].sum()
    total_estimated_units = products["estimated_units"].sum()
    total_daily_value = products["estimated_daily_value"].sum()
    total_estimated_value = products["estimated_value"].sum()

    # ======================================
    # KPI CARDS
    # ======================================

    st.subheader("Demand Overview")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Products Analysed",
        f"{len(products):,}"
    )

    c2.metric(
        "Estimated Daily Demand",
        f"{total_daily_demand:,.1f} units"
    )

    c3.metric(
        "Estimated Daily Sales Value",
        f"₹{total_daily_value:,.2f}"
    )

    c4.metric(
        f"Estimated Value ({period} days)",
        f"₹{total_estimated_value:,.2f}"
    )

    st.caption(
        f"Estimated demand for the selected period: "
        f"{total_estimated_units:,.1f} units."
    )

    st.info(
        "These are estimates based on average daily sales from "
        "inventory records and the available unit prices. "
        "They are not actual recorded sales or confirmed revenue."
    )

    st.divider()

    # ======================================
    # PRODUCT DEMAND ANALYSIS
    # ======================================

    st.subheader("Top Products by Estimated Demand")

    top_products = (
        products.sort_values(
            "estimated_units", ascending=False
        ).head(10)
    )

    fig_products = px.bar(
        top_products.sort_values("estimated_units"),
        x="estimated_units",
        y="product_name",
        orientation="h",
        text="estimated_units",
        title=f"Estimated Product Demand - {period} Days",
        color="estimated_units",
        color_continuous_scale=["#245B4A", GREEN_LIGHT],
        labels={
            "estimated_units": "Estimated Units",
            "product_name": "Product",
        },
    )

    fig_products.update_traces(
        texttemplate="%{x:,.1f}",
        textposition="outside",
        cliponaxis=False,
    )

    fig_products.update_layout(
        template="plotly_dark",
        paper_bgcolor=PANEL,
        plot_bgcolor=PANEL,
        font=dict(color=TEXT, size=13),
        height=450,
        showlegend=False,
        margin=dict(l=30, r=55, t=65, b=50),
    )

    st.plotly_chart(
        fig_products,
        use_container_width=True,
        config={"displayModeBar": False},
    )

    st.divider()

    # ======================================
    # CATEGORY DEMAND
    # ======================================

    st.subheader("Category-wise Estimated Demand")

    category_summary = (
        products.groupby("category", as_index=False)
        .agg(
            Estimated_Daily_Demand=("daily_demand", "sum"),
            Estimated_Daily_Value=("estimated_daily_value", "sum"),
            Available_Stock=("available_stock", "sum"),
        )
        .sort_values(
            "Estimated_Daily_Demand", ascending=False
        )
    )

    fig_category = px.bar(
        category_summary,
        x="category",
        y="Estimated_Daily_Demand",
        color="category",
        text="Estimated_Daily_Demand",
        title="Daily Demand by Product Category",
        labels={
            "category": "Category",
            "Estimated_Daily_Demand": "Estimated Units per Day",
        },
    )

    fig_category.update_traces(
        texttemplate="%{y:,.1f}",
        textposition="outside",
        cliponaxis=False,
    )

    fig_category.update_layout(
        template="plotly_dark",
        paper_bgcolor=PANEL,
        plot_bgcolor=PANEL,
        font=dict(color=TEXT, size=13),
        height=400,
        showlegend=False,
        margin=dict(l=45, r=45, t=65, b=75),
    )

    fig_category.update_xaxes(tickangle=-20)

    st.plotly_chart(
        fig_category,
        use_container_width=True,
        config={"displayModeBar": False},
    )

    st.divider()

    # ======================================
    # DEMAND VS AVAILABLE STOCK
    # ======================================

    st.subheader("Estimated Demand vs Available Stock")

    comparison = products[
        [
            "product_name",
            "available_stock",
            "estimated_units",
            "stock_coverage_days",
            "estimated_value",
        ]
    ].copy()

    comparison["Stock Status"] = comparison[
        "stock_coverage_days"
    ].apply(
        lambda days:
            "Low Coverage" if pd.notna(days) and days <= 7
            else "Adequate Coverage" if pd.notna(days)
            else "No Demand Data"
    )

    comparison = comparison.sort_values(
        "stock_coverage_days",
        na_position="first",
    )

    st.dataframe(
        comparison,
        use_container_width=True,
        hide_index=True,
        column_config={
            "product_name": st.column_config.TextColumn(
                "Product",
                width="medium",
            ),
            "available_stock": st.column_config.NumberColumn(
                "Available Stock",
                format="%,.0f",
            ),
            "estimated_units": st.column_config.NumberColumn(
                f"Estimated Demand ({period} days)",
                format="%,.1f",
            ),
            "stock_coverage_days": st.column_config.NumberColumn(
                "Stock Coverage",
                format="%.1f days",
            ),
            "estimated_value": st.column_config.NumberColumn(
                "Estimated Value",
                format="₹ %,.2f",
            ),
            "Stock Status": st.column_config.TextColumn(
                "Stock Status",
            ),
        },
    )

    low_coverage = comparison[
        comparison["Stock Status"] == "Low Coverage"
    ]

    if not low_coverage.empty:
        st.warning(
            f"{len(low_coverage)} products have estimated "
            "stock coverage of 7 days or less. Review replenishment."
        )
    else:
        st.success(
            "No products with 7 days or less of estimated stock coverage."
        )

    st.caption(
        "Method: product-level average of avg_daily_sales_7d is used "
        "as the daily demand estimate. Available stock is summed across "
        "the product's inventory batches. Estimated value uses unit_price. "
        "This page does not represent actual sales transactions."
    )
