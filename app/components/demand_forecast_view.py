import pandas as pd
import plotly.express as px
import streamlit as st

PANEL = "#192630"
TEXT = "#F1F5F7"
GREEN = "#35C99A"
AMBER = "#F2B84B"
RED = "#EF6B68"


def show_demand_forecasts(df):

    st.title("Demand Forecasts")
    st.caption(
        "Estimate future product demand using available inventory "
        "and average daily sales information."
    )

    if df is None or df.empty:
        st.warning("No inventory data is available.")
        return

    required = [
        "product_id",
        "product_name",
        "quantity_remaining",
        "avg_daily_sales_7d",
    ]

    missing = [c for c in required if c not in df.columns]

    if missing:
        st.error("Missing columns: " + ", ".join(missing))
        return

    data = df.copy()

    data["quantity_remaining"] = pd.to_numeric(
        data["quantity_remaining"], errors="coerce"
    ).fillna(0).clip(lower=0)

    data["avg_daily_sales_7d"] = pd.to_numeric(
        data["avg_daily_sales_7d"], errors="coerce"
    ).clip(lower=0)

    aggregations = {
        "product_name": ("product_name", "first"),
        "available_stock": ("quantity_remaining", "sum"),
        "daily_demand": ("avg_daily_sales_7d", "mean"),
    }

    if "category" in data.columns:
        aggregations["category"] = ("category", "first")

    products = (
        data.groupby("product_id", as_index=False)
        .agg(**aggregations)
    )

    if "category" not in products.columns:
        products["category"] = "Uncategorized"

    products["category"] = (
        products["category"].fillna("Uncategorized")
    )

    products["daily_demand"] = (
        products["daily_demand"].clip(lower=0)
    )

    if products["daily_demand"].notna().sum() == 0:
        st.warning("Average daily demand data is unavailable.")
        return

    # ======================================
    # FORECAST SETTINGS
    # ======================================

    st.subheader("Forecast Settings")

    period = st.selectbox(
        "Forecast Horizon",
        options=[7, 15, 30],
        index=0,
        format_func=lambda x: f"Next {x} Days",
    )

    products["forecast_units"] = (
        products["daily_demand"] * period
    )

    products["stock_coverage_days"] = (
        products["available_stock"]
        / products["daily_demand"].where(
            products["daily_demand"] > 0
        )
    )

    products["remaining_after_forecast"] = (
        products["available_stock"]
        - products["forecast_units"]
    )

    products["forecast_status"] = products.apply(
        lambda row:
            "Insufficient Stock"
            if pd.notna(row["daily_demand"])
            and row["daily_demand"] > 0
            and row["remaining_after_forecast"] < 0
            else "Low Coverage"
            if pd.notna(row["stock_coverage_days"])
            and row["stock_coverage_days"] <= period
            else "Sufficient Stock"
            if pd.notna(row["daily_demand"])
            and row["daily_demand"] > 0
            else "Demand Data Missing",
        axis=1,
    )

    total_demand = products["daily_demand"].sum()
    total_forecast = products["forecast_units"].sum()

    # ======================================
    # KPI CARDS
    # ======================================

    st.subheader("Forecast Overview")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Products Analysed",
        f"{len(products):,}",
    )

    c2.metric(
        "Average Daily Demand",
        f"{total_demand:,.1f} units",
    )

    c3.metric(
        f"{period}-Day Forecast",
        f"{total_forecast:,.1f} units",
    )

    c4.metric(
        "Insufficient Stock",
        f"{(products['forecast_status'] == 'Insufficient Stock').sum():,}",
    )

    st.info(
        "Forecast method: product-level average of avg_daily_sales_7d "
        "multiplied by the selected number of days. This is a baseline "
        "estimate, not a trained time-series model or guaranteed demand."
    )

    st.divider()

    # ======================================
    # DAILY FORECAST
    # ======================================

    st.subheader("Estimated Daily Demand")

    daily_forecast = pd.DataFrame({
        "Day": range(1, period + 1),
        "Estimated Demand": [total_demand] * period,
    })

    fig_daily = px.line(
        daily_forecast,
        x="Day",
        y="Estimated Demand",
        markers=True,
        title=f"Baseline Daily Demand - Next {period} Days",
    )

    fig_daily.update_traces(
        line=dict(color=GREEN, width=3),
        marker=dict(size=7),
    )

    fig_daily.update_layout(
        template="plotly_dark",
        paper_bgcolor=PANEL,
        plot_bgcolor=PANEL,
        font=dict(color=TEXT, size=13),
        height=390,
        xaxis_title="Forecast Day",
        yaxis_title="Estimated Units",
    )

    st.plotly_chart(
        fig_daily,
        use_container_width=True,
        config={"displayModeBar": False},
    )

    st.caption(
        "The flat line represents a constant-demand baseline. "
        "It does not show a historical or predicted seasonal trend."
    )

    st.divider()

    # ======================================
    # PRODUCT FORECAST
    # ======================================

    st.subheader("Product-wise Demand Forecast")

    top_products = (
        products.sort_values(
            "forecast_units", ascending=False
        ).head(10).sort_values("forecast_units")
    )

    fig_products = px.bar(
        top_products,
        x="forecast_units",
        y="product_name",
        orientation="h",
        text="forecast_units",
        color="forecast_units",
        color_continuous_scale=["#245B4A", GREEN],
        title=f"Top 10 Products - {period}-Day Demand",
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
        height=430,
        xaxis_title="Estimated Units",
        yaxis_title="Product",
        showlegend=False,
    )

    st.plotly_chart(
        fig_products,
        use_container_width=True,
        config={"displayModeBar": False},
    )

    st.divider()

    # ======================================
    # CATEGORY FORECAST
    # ======================================

    st.subheader("Category-wise Forecast")

    category_data = (
        products.groupby("category", as_index=False)
        .agg(
            Forecast_Units=("forecast_units", "sum"),
            Available_Stock=("available_stock", "sum"),
        )
        .sort_values("Forecast_Units", ascending=False)
    )

    fig_category = px.bar(
        category_data,
        x="category",
        y="Forecast_Units",
        color="category",
        text="Forecast_Units",
        title=f"Category Demand - {period} Days",
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
        height=390,
        showlegend=False,
        xaxis_title="Category",
        yaxis_title="Estimated Units",
    )

    st.plotly_chart(
        fig_category,
        use_container_width=True,
        config={"displayModeBar": False},
    )

    st.divider()

    # ======================================
    # STOCK VS FORECAST
    # ======================================

    st.subheader("Forecast Demand vs Available Stock")

    result = products[
        [
            "product_name",
            "category",
            "daily_demand",
            "forecast_units",
            "available_stock",
            "remaining_after_forecast",
            "stock_coverage_days",
            "forecast_status",
        ]
    ].sort_values(
        "remaining_after_forecast",
        ascending=True,
    )

    st.dataframe(
        result,
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
            "daily_demand": st.column_config.NumberColumn(
                "Daily Demand",
                format="%.2f",
            ),
            "forecast_units": st.column_config.NumberColumn(
                f"Forecast ({period} days)",
                format="%,.1f",
            ),
            "available_stock": st.column_config.NumberColumn(
                "Available Stock",
                format="%,.0f",
            ),
            "remaining_after_forecast": st.column_config.NumberColumn(
                "Estimated Remaining Stock",
                format="%,.1f",
            ),
            "stock_coverage_days": st.column_config.NumberColumn(
                "Stock Coverage",
                format="%.1f days",
            ),
            "forecast_status": st.column_config.TextColumn(
                "Forecast Status"
            ),
        },
    )

    # ======================================
    # ATTENTION REQUIRED
    # ======================================

    attention = products[
        products["forecast_status"].isin(
            ["Insufficient Stock", "Low Coverage"]
        )
    ]

    st.subheader("Products Requiring Attention")

    if attention.empty:
        st.success(
            "No products require additional attention "
            "for this forecast horizon."
        )
    else:
        st.warning(
            f"{len(attention)} products require stock coverage review."
        )

        st.dataframe(
            attention[
                [
                    "product_name",
                    "available_stock",
                    "forecast_units",
                    "stock_coverage_days",
                    "forecast_status",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

    # ======================================
    # EXPORT
    # ======================================

    st.divider()
    st.subheader("Export Forecast Report")

    st.download_button(
        "Download Demand Forecast CSV",
        data=products.to_csv(index=False).encode("utf-8"),
        file_name=f"wastewise_demand_forecast_{period}_days.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.caption(
        "WasteWise AI | Baseline demand estimates based on "
        "available inventory records."
    )
