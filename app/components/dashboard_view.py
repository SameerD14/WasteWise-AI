import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import text
from src.database.connection import engine

from app.components.ui import (
    page_header,
    kpi_card,
    format_currency,
    section_header,
    empty_state,
)

# ==========================================
# WASTEWISE AI - DARK DASHBOARD
# ==========================================

BG = "#101820"
PANEL = "#192630"
GREEN = "#16A879"
GREEN_LIGHT = "#35C99A"
TEAL = "#35A995"
AMBER = "#F2B84B"
RED = "#EF6B68"
TEXT = "#F1F5F7"
MUTED = "#A6B5BF"
GRID = "#30414D"


def apply_chart_style(fig, height=380):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=PANEL,
        plot_bgcolor=PANEL,
        height=height,
        font=dict(
            family="Inter, Arial, sans-serif",
            size=14,
            color=TEXT,
        ),
        title=dict(
            font=dict(size=19, color=TEXT),
            x=0.03,
            xanchor="left",
        ),
        legend=dict(
            font=dict(color=TEXT),
            title_font=dict(color=TEXT),
        ),
        margin=dict(l=65, r=45, t=75, b=65),
        hoverlabel=dict(
            bgcolor="#223440",
            font=dict(color=TEXT),
        ),
    )

    fig.update_xaxes(
        tickfont=dict(color=MUTED, size=13),
        title_font=dict(color=TEXT),
        gridcolor=GRID,
        zerolinecolor=GRID,
    )

    fig.update_yaxes(
        tickfont=dict(color=MUTED, size=13),
        title_font=dict(color=TEXT),
        gridcolor=GRID,
        zerolinecolor=GRID,
    )

    return fig


def show_dashboard(df):

    # ======================================
    # PAGE HEADER
    # ======================================

    page_header(
        "Dashboard",
        "Overview of your inventory health, stock performance and expiry risk."
    )

    if df is None or df.empty:
        empty_state(
            "No inventory records",
            "Load inventory data into MySQL to see your dashboard."
        )
        return

    data = df.copy()

    required = [
        "product_id",
        "product_name",
        "batch_id",
        "quantity_remaining",
        "unit_cost",
        "days_to_expiry",
        "risk_status",
        "priority",
        "recommended_action",
    ]

    missing = [col for col in required if col not in data.columns]

    if missing:
        st.error("Dashboard data is missing required columns: " + ", ".join(missing))
        return

    # ======================================
    # DATA PREPARATION
    # ======================================

    numeric_columns = [
        "quantity_remaining",
        "initial_quantity",
        "unit_cost",
        "unit_price",
        "days_to_expiry",
        "stock_coverage_days",
        "avg_daily_sales_7d",
        "expected_demand_before_expiry",
        "inventory_surplus",
        "risk_probability",
    ]

    for col in numeric_columns:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

    data["quantity_remaining"] = data["quantity_remaining"].fillna(0)
    data["unit_cost"] = data["unit_cost"].fillna(0)

    # ======================================
    # BUSINESS METRICS
    # ======================================

    total_products = data["product_id"].nunique()
    total_batches = len(data)

    high_risk = (data["risk_status"] == "High Risk").sum()
    expired = (data["risk_status"] == "Expired").sum()

    expires_today = (
        data["risk_status"] == "Expires Today - Immediate Review"
    ).sum()

    remaining_stock = data["quantity_remaining"].sum()

    inventory_value = (
        data["quantity_remaining"] * data["unit_cost"]
    ).sum()

    if "stock_coverage_days" in data.columns:
        coverage = data["stock_coverage_days"]
        valid_coverage = coverage.dropna()

        stock_health = (
            (valid_coverage >= 30).mean() * 100
            if not valid_coverage.empty else 0
        )

        low_stock = (coverage.notna() & (coverage <= 7)).sum()
        overstock = (coverage >= 90).sum()

        overstock_value = (
            data.loc[coverage >= 90, "quantity_remaining"]
            * data.loc[coverage >= 90, "unit_cost"]
        ).sum()
    else:
        stock_health = 0
        low_stock = 0
        overstock = 0
        overstock_value = 0

    # ======================================
    # STOCK HEALTH SUMMARY
    # ======================================

    st.markdown("## 📊 Stock Health")

    health_col, low_col, over_col = st.columns([2, 1, 1])

    with health_col:
        st.markdown(
            f"""
            <div class="ww-kpi-card" style="border-left:4px solid {GREEN};">
                <div class="ww-kpi-label">Stock Health</div>
                <div class="ww-kpi-value">{stock_health:.1f}%</div>
                <div class="ww-kpi-help">
                    Percentage of batches with 30 or more days of stock coverage
                </div>
                <div style="background:#30414D;border-radius:10px;height:9px;margin-top:15px;">
                    <div style="background:{GREEN};width:{min(stock_health, 100):.1f}%;height:9px;border-radius:10px;"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with low_col:
        kpi_card(
            "Low Stock Batches",
            f"{low_stock:,}",
            "7 days or less of stock coverage"
        )

    with over_col:
        kpi_card(
            "Overstock Batches",
            f"{overstock:,}",
            "90 days or more of stock coverage"
        )

    if overstock > 0:
        st.warning(
            f"Overstock attention: {overstock:,} batches have 90+ days "
            f"of coverage. Their inventory cost value is "
            f"{format_currency(overstock_value)}."
        )

    # ======================================
    # MAIN KPI CARDS
    # ======================================

    section_header("📦 Inventory Performance", "A quick summary of your current inventory position.")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        kpi_card("📦 Total Products", f"{total_products:,}")

    with c2:
        kpi_card("🗂️ Inventory Batches", f"{total_batches:,}")

    with c3:
        kpi_card("🔴 High Risk Batches", f"{high_risk:,}")

    with c4:
        kpi_card("⛔ Expired Batches", f"{expired:,}")

    c5, c6, c7 = st.columns(3)

    with c5:
        kpi_card("⏰ Expires Today", f"{expires_today:,}")

    with c6:
        kpi_card("📊 Remaining Stock", f"{remaining_stock:,.0f}")

    with c7:
        kpi_card("💰 Inventory Cost Value", format_currency(inventory_value))

    # ======================================
    # STOCK MOVEMENT SUMMARY
    # ======================================

    st.divider()
    section_header(
        "🔄 Stock Movement Activity",
        "Track received, sold, consumed, wasted, and adjusted stock."
    )

    with engine.connect() as conn:
        movement_summary = pd.read_sql(
            text("""
                SELECT
                    COUNT(*) AS total_movements,
                    COALESCE(SUM(CASE WHEN movement_type = 'Received'
                        THEN quantity ELSE 0 END), 0) AS units_received,
                    COALESCE(SUM(CASE WHEN movement_type = 'Sold'
                        THEN quantity ELSE 0 END), 0) AS units_sold,
                    COALESCE(SUM(CASE WHEN movement_type = 'Consumed'
                        THEN quantity ELSE 0 END), 0) AS units_consumed,
                    COALESCE(SUM(CASE WHEN movement_type = 'Wasted'
                        THEN quantity ELSE 0 END), 0) AS units_wasted
                FROM stock_movements
            """),
            conn
        )

        recent_movements = pd.read_sql(
            text("""
                SELECT
                    sm.movement_date,
                    sm.batch_id,
                    p.product_name,
                    sm.movement_type,
                    sm.quantity,
                    sm.previous_quantity,
                    sm.new_quantity,
                    sm.reason
                FROM stock_movements sm
                JOIN inventory_batches ib
                    ON sm.batch_id = ib.batch_id
                JOIN products p
                    ON ib.product_id = p.product_id
                ORDER BY sm.movement_id DESC
                LIMIT 10
            """),
            conn
        )

    movement = movement_summary.iloc[0]

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        kpi_card("Total Movements", f"{int(movement['total_movements']):,}")
    with m2:
        kpi_card("Units Received", f"{int(movement['units_received']):,}")
    with m3:
        kpi_card("Units Sold", f"{int(movement['units_sold']):,}")
    with m4:
        kpi_card("Units Consumed", f"{int(movement['units_consumed']):,}")
    with m5:
        kpi_card("Units Wasted", f"{int(movement['units_wasted']):,}")

    st.markdown("#### Recent Stock Movements")
    if recent_movements.empty:
        st.info("No stock movements recorded yet.")
    else:
        st.dataframe(
            recent_movements,
            use_container_width=True,
            hide_index=True
        )

    # ======================================
    # INVENTORY ANALYTICS
    # ======================================

    section_header(
        "📈 Inventory Analytics",
        "Understand stock priority and expiry risk across your inventory."
    )

    left, right = st.columns(2)

    with left:
        priority_data = (
            data["priority"]
            .fillna("Unknown")
            .value_counts()
            .rename_axis("Priority")
            .reset_index(name="Batches")
        )

        priority_colors = {
            "Critical": RED,
            "High": AMBER,
            "Review": TEAL,
            "Normal": GREEN,
            "Unknown": MUTED,
        }

        fig_priority = px.pie(
            priority_data,
            names="Priority",
            values="Batches",
            hole=0.62,
            title="Inventory Priority Distribution",
            color="Priority",
            color_discrete_map=priority_colors,
        )

        fig_priority.update_traces(
            textposition="inside",
            textinfo="percent",
            textfont=dict(color="#FFFFFF", size=13),
            marker=dict(
                line=dict(color=PANEL, width=3)
            ),
            hovertemplate=(
                "<b>%{label}</b><br>"
                "Batches: %{value:,}<br>"
                "Share: %{percent}<extra></extra>"
            ),
        )

        fig_priority = apply_chart_style(fig_priority)

        st.plotly_chart(
            fig_priority,
            use_container_width=True,
            config={"displayModeBar": False},
        )

    with right:
        risk_data = (
            data["risk_status"]
            .fillna("Unknown")
            .value_counts()
            .rename_axis("Risk Status")
            .reset_index(name="Batches")
        )

        risk_colors = {
            "Low Risk": GREEN,
            "High Risk": RED,
            "Expired": AMBER,
            "Expires Today - Immediate Review": TEAL,
            "Unknown": MUTED,
        }

        fig_risk = px.bar(
            risk_data,
            x="Risk Status",
            y="Batches",
            color="Risk Status",
            title="Expiry Risk Distribution",
            text="Batches",
            color_discrete_map=risk_colors,
        )

        fig_risk.update_traces(
            textposition="outside",
            textfont=dict(color=TEXT, size=12),
            cliponaxis=False,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Batches: %{y:,}<extra></extra>"
            ),
        )

        fig_risk.update_layout(showlegend=False)
        fig_risk.update_xaxes(tickangle=-20)

        fig_risk = apply_chart_style(fig_risk)

        st.plotly_chart(
            fig_risk,
            use_container_width=True,
            config={"displayModeBar": False},
        )

    st.divider()


    # ======================================
    # CATEGORY AND UPCOMING EXPIRY ANALYTICS
    # ======================================

    section_header(
        "📊 Category & Expiry Analytics",
        "Compare stock across categories and identify upcoming expiry batches."
    )

    category_col, expiry_col = st.columns(2)

    with category_col:
        if "category" in data.columns:
            category_data = (
                data.assign(
                    category=data["category"].fillna("Uncategorized")
                )
                .groupby("category", as_index=False)
                .agg(
                    Remaining_Stock=("quantity_remaining", "sum"),
                    Total_Batches=("batch_id", "count")
                )
                .sort_values("Remaining_Stock", ascending=False)
                .head(12)
            )

            fig_category = px.bar(
                category_data,
                x="Remaining_Stock",
                y="category",
                orientation="h",
                text="Remaining_Stock",
                title="Remaining Stock by Category",
                color="Remaining_Stock",
                color_continuous_scale=["#245B4A", GREEN_LIGHT],
                hover_data=["Total_Batches"]
            )

            fig_category.update_traces(
                texttemplate="%{x:,.0f}",
                textposition="outside",
                cliponaxis=False
            )

            fig_category.update_layout(
                yaxis=dict(categoryorder="total ascending"),
                showlegend=False
            )

            fig_category = apply_chart_style(fig_category, height=430)

            st.plotly_chart(
                fig_category,
                use_container_width=True,
                config={"displayModeBar": False}
            )
        else:
            st.info("Category information is not available.")

    with expiry_col:
        expiry_days = data["days_to_expiry"]

        expiry_data = data[["batch_id"]].copy()
        expiry_data["Expiry Window"] = "Unknown"

        expiry_data.loc[
            expiry_days < 0, "Expiry Window"
        ] = "Expired"

        expiry_data.loc[
            expiry_days.between(0, 7, inclusive="both"),
            "Expiry Window"
        ] = "0–7 Days"

        expiry_data.loc[
            expiry_days.gt(7) & expiry_days.le(15),
            "Expiry Window"
        ] = "8–15 Days"

        expiry_data.loc[
            expiry_days.gt(15) & expiry_days.le(30),
            "Expiry Window"
        ] = "16–30 Days"

        expiry_data.loc[
            expiry_days.gt(30),
            "Expiry Window"
        ] = "31+ Days"

        expiry_order = [
            "Expired",
            "0–7 Days",
            "8–15 Days",
            "16–30 Days",
            "31+ Days",
            "Unknown"
        ]

        expiry_summary = (
            expiry_data["Expiry Window"]
            .value_counts()
            .reindex(expiry_order, fill_value=0)
            .rename_axis("Expiry Window")
            .reset_index(name="Batches")
        )

        fig_expiry = px.bar(
            expiry_summary,
            x="Expiry Window",
            y="Batches",
            title="Upcoming Expiry Window",
            text="Batches",
            color="Expiry Window",
            color_discrete_map={
                "Expired": RED,
                "0–7 Days": AMBER,
                "8–15 Days": "#E89A48",
                "16–30 Days": TEAL,
                "31+ Days": GREEN,
                "Unknown": MUTED
            }
        )

        fig_expiry.update_traces(
            textposition="outside",
            cliponaxis=False
        )

        fig_expiry.update_layout(
            showlegend=False
        )

        fig_expiry = apply_chart_style(fig_expiry, height=430)

        st.plotly_chart(
            fig_expiry,
            use_container_width=True,
            config={"displayModeBar": False}
        )

    st.divider()

    # ======================================
    # PRODUCT STOCK ANALYSIS
    # ======================================

    section_header(
        "🏷️ Product Stock Analysis",
        "Top 10 products ranked by remaining inventory."
    )

    product_summary = (
        data.groupby("product_name", as_index=False)
        .agg(
            Remaining_Stock=("quantity_remaining", "sum"),
            Total_Batches=("batch_id", "count"),
        )
        .sort_values("Remaining_Stock", ascending=False)
        .head(10)
    )

    fig_products = px.bar(
        product_summary,
        x="Remaining_Stock",
        y="product_name",
        orientation="h",
        text="Remaining_Stock",
        title="Top 10 Products by Remaining Stock",
        color="Remaining_Stock",
        color_continuous_scale=["#245B4A", GREEN_LIGHT],
        hover_data=["Total_Batches"],
    )

    fig_products.update_traces(
        texttemplate="%{x:,.0f}",
        textposition="outside",
        textfont=dict(color=TEXT, size=12),
        cliponaxis=False,
    )

    fig_products.update_layout(
        coloraxis_colorbar=dict(
            title="Remaining Stock",
            tickfont=dict(color=TEXT),
        ),
        yaxis=dict(categoryorder="total ascending"),
    )

    fig_products = apply_chart_style(fig_products, height=430)

    st.plotly_chart(
        fig_products,
        use_container_width=True,
        config={"displayModeBar": False},
    )

    st.divider()

    # ======================================
    # INVENTORY ATTENTION REQUIRED
    # ======================================

    section_header(
        "⚠️ Inventory Attention Required",
        "Batches that need immediate inventory or expiry action."
    )

    alerts = data[
        data["risk_status"].isin([
            "High Risk",
            "Expired",
            "Expires Today - Immediate Review",
        ])
    ].copy()

    alerts = alerts.sort_values(
        "days_to_expiry",
        na_position="first",
    )

    if alerts.empty:
        st.success("No inventory alerts found.")
    else:
        display_columns = [
            "batch_id",
            "product_name",
            "days_to_expiry",
            "risk_status",
            "priority",
            "recommended_action",
        ]

        st.dataframe(
            alerts[display_columns].head(20),
            use_container_width=True,
            hide_index=True,
            height=500,
            column_config={
                "batch_id": st.column_config.NumberColumn("Batch ID", width="small"),
                "product_name": st.column_config.TextColumn("Product", width="medium"),
                "days_to_expiry": st.column_config.NumberColumn(
                    "Days to Expiry",
                    format="%d days",
                ),
                "risk_status": st.column_config.TextColumn("Expiry Risk", width="medium"),
                "priority": st.column_config.TextColumn("Priority", width="small"),
                "recommended_action": st.column_config.TextColumn(
                    "Recommended Action",
                    width="large",
                ),
            },
        )

    # ======================================
    # FOOTNOTE
    # ======================================

    st.caption(
        "Inventory cost value = remaining quantity × unit cost. "
        "Stock health uses 30+ days of stock coverage; low stock uses "
        "7 days or less; overstock uses 90 days or more. "
        "ML risk labels are based on synthetic training labels and "
        "are not independently validated real-world predictions."
    )
