
import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import text

from src.database.connection import engine
from app.components.ui import page_header, format_currency


# =====================================================
# 1. FILTER RESET
# =====================================================

def reset_inventory_filters():

    st.session_state["inv_product"] = "All Products"
    st.session_state["inv_category"] = "All Categories"
    st.session_state["inv_risk"] = "All Risk Statuses"
    st.session_state["inv_expiry"] = "All Batches"
    st.session_state["inv_batch"] = "All Batches"


# =====================================================
# 2. PROFESSIONAL CHART THEME
# =====================================================

NAVY = "#142B3B"
EMERALD = "#138A68"
CORAL = "#DC665B"
AMBER = "#E9A23B"
TEAL = "#35A995"


def style_chart(fig, title):

    fig.update_layout(
        title={
            "text": title,
            "font": {
                "size": 19,
                "color": NAVY
            }
        },
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font={
            "family": "Arial",
            "size": 13,
            "color": "#34495A"
        },
        margin=dict(l=30, r=30, t=65, b=45),
        showlegend=False,
        coloraxis_showscale=False
    )

    fig.update_xaxes(
        title_font=dict(color=NAVY, size=13),
        tickfont=dict(color="#34495A", size=12),
        gridcolor="#E5ECE8",
        zerolinecolor="#C9D6D0"
    )

    fig.update_yaxes(
        title_font=dict(color=NAVY, size=13),
        tickfont=dict(color="#34495A", size=12),
        gridcolor="#E5ECE8",
        zerolinecolor="#C9D6D0"
    )

    return fig


# =====================================================
# 3. INVENTORY MANAGEMENT
# =====================================================

def show_inventory(df):

    page_header(
        "Inventory Management",
        "Manage stock, track batches and monitor product expiry."
    )

    if df.empty:
        st.warning("No inventory records available.")
        return

    data = df.copy()

    # Convert numeric columns safely
    numeric_columns = [
        "batch_id",
        "quantity_remaining",
        "initial_quantity",
        "unit_cost",
        "days_to_expiry",
        "inventory_surplus"
    ]

    for column in numeric_columns:

        if column in data.columns:
            data[column] = pd.to_numeric(
                data[column],
                errors="coerce"
            )

    data["quantity_remaining"] = (
        data["quantity_remaining"].fillna(0)
    )

    # =================================================
    # 4. KPI METRICS
    # =================================================

    total_batches = len(data)

    total_stock = data["quantity_remaining"].sum()

    expired = (
        data["days_to_expiry"] < 0
    ).sum()

    expiring_soon = (
        (data["days_to_expiry"] >= 0)
        & (data["days_to_expiry"] <= 3)
    ).sum()

    unknown_expiry = data["days_to_expiry"].isna().sum()

    high_risk = (
        data["risk_status"] == "High Risk"
    ).sum()

    inventory_value = (
        data["quantity_remaining"] * data["unit_cost"]
    ).sum()

    st.subheader("Inventory Performance")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total Batches", f"{total_batches:,}")
    c2.metric("Remaining Stock", f"{total_stock:,.0f}")
    c3.metric("Expired Batches", f"{expired:,}")
    c4.metric("High Risk Batches", f"{high_risk:,}")

    c5, c6, c7 = st.columns(3)

    c5.metric(
        "Expiring Within 3 Days",
        f"{expiring_soon:,}"
    )

    c6.metric(
        "Unknown Expiry Batches",
        f"{unknown_expiry:,}"
    )

    c7.metric(
        "Inventory Cost Value",
        format_currency(inventory_value)
    )

    st.divider()

    # =================================================
    # 5. FILTER OPTIONS
    # =================================================

    st.subheader("Find Inventory")

    st.caption(
        "Choose from the available products and batches. "
        "You do not need to remember or type their IDs."
    )

    # Build product options
    product_names = sorted(
        data["product_name"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    product_options = ["All Products"] + product_names

    # Build category options
    category_names = sorted(
        data["category"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    category_options = ["All Categories"] + category_names

    # Build risk options
    risk_names = sorted(
        data["risk_status"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    risk_options = ["All Risk Statuses"] + risk_names

    # Reset filters button
    reset_col, info_col = st.columns([1, 3])

    with reset_col:

        st.button(
            "↻ Reset Filters",
            on_click=reset_inventory_filters,
            use_container_width=True
        )

    with info_col:

        st.caption(
            "Filters update the inventory results automatically."
        )

    # =================================================
    # 6. PRODUCT AND CATEGORY FILTERS
    # =================================================

    f1, f2 = st.columns(2)

    with f1:

        selected_product = st.selectbox(
            "Select Product",
            product_options,
            key="inv_product"
        )

    with f2:

        selected_category = st.selectbox(
            "Select Category",
            category_options,
            key="inv_category"
        )

    # =================================================
    # 7. RISK AND EXPIRY FILTERS
    # =================================================

    f3, f4 = st.columns(2)

    with f3:

        selected_risk = st.selectbox(
            "Select Risk Status",
            risk_options,
            key="inv_risk"
        )

    with f4:

        expiry_options = [
            "All Batches",
            "Expired",
            "Expires Today",
            "Expires Within 3 Days",
            "Expires Within 7 Days",
            "More Than 7 Days",
            "Expiry Unknown"
        ]

        selected_expiry = st.selectbox(
            "Select Expiry Period",
            expiry_options,
            key="inv_expiry"
        )

    # =================================================
    # 8. APPLY PRODUCT, CATEGORY, RISK AND EXPIRY
    # =================================================

    filtered = data.copy()

    if selected_product != "All Products":

        filtered = filtered[
            filtered["product_name"] == selected_product
        ]

    if selected_category != "All Categories":

        filtered = filtered[
            filtered["category"] == selected_category
        ]

    if selected_risk != "All Risk Statuses":

        filtered = filtered[
            filtered["risk_status"] == selected_risk
        ]

    days = filtered["days_to_expiry"]

    if selected_expiry == "Expired":

        filtered = filtered[days < 0]

    elif selected_expiry == "Expires Today":

        filtered = filtered[days == 0]

    elif selected_expiry == "Expires Within 3 Days":

        filtered = filtered[
            (days >= 0) & (days <= 3)
        ]

    elif selected_expiry == "Expires Within 7 Days":

        filtered = filtered[
            (days >= 0) & (days <= 7)
        ]

    elif selected_expiry == "More Than 7 Days":

        filtered = filtered[days > 7]

    elif selected_expiry == "Expiry Unknown":

        filtered = filtered[days.isna()]

    # =================================================
    # 9. BATCH SELECTION
    # =================================================

    st.markdown("#### Select Individual Batch")

    # Create readable labels using ID + product + expiry
    batch_labels = {}

    for _, row in filtered.iterrows():

        batch_id = int(row["batch_id"])

        product_name = str(row["product_name"])

        risk = str(row["risk_status"])

        days_left = row["days_to_expiry"]

        if pd.isna(days_left):
            expiry_text = "Expiry unknown"
        else:
            expiry_text = f"{int(days_left)} days to expiry"

        batch_labels[batch_id] = (
            f"Batch {batch_id} | {product_name} | "
            f"{risk} | {expiry_text}"
        )

    batch_ids = sorted(batch_labels.keys())

    batch_options = ["All Batches"] + batch_ids

    selected_batch = st.selectbox(
        "Choose Batch",
        batch_options,
        format_func=lambda x: (
            x if x == "All Batches"
            else batch_labels.get(x, str(x))
        ),
        key="inv_batch"
    )

    if selected_batch != "All Batches":

        filtered = filtered[
            filtered["batch_id"] == selected_batch
        ]

    # =================================================
    # 10. FILTER SUMMARY
    # =================================================

    st.divider()

    st.subheader("Inventory Batch Catalogue")

    summary_col1, summary_col2 = st.columns(2)

    summary_col1.metric(
        "Matching Batches",
        f"{len(filtered):,}"
    )

    summary_col2.metric(
        "Matching Stock",
        f"{filtered['quantity_remaining'].sum():,.0f}"
    )

    # =================================================
    # 11. INVENTORY TABLE
    # =================================================

    display_columns = [
        "batch_id",
        "product_name",
        "category",
        "quantity_remaining",
        "expiry_date",
        "days_to_expiry",
        "risk_status",
        "priority",
        "recommended_action"
    ]

    if filtered.empty:

        st.info(
            "No inventory batches match your selected filters. "
            "Try changing the filters or select Reset Filters."
        )

    else:

        st.dataframe(
            filtered[display_columns],
            use_container_width=True,
            hide_index=True,
            height=420,
            column_config={

                "batch_id": st.column_config.NumberColumn(
                    "Batch ID",
                    format="%d"
                ),

                "product_name": st.column_config.TextColumn(
                    "Product"
                ),

                "category": st.column_config.TextColumn(
                    "Category"
                ),

                "quantity_remaining": st.column_config.NumberColumn(
                    "Remaining Stock",
                    format="%d"
                ),

                "expiry_date": st.column_config.DateColumn(
                    "Expiry Date",
                    format="DD MMM YYYY"
                ),

                "days_to_expiry": st.column_config.NumberColumn(
                    "Days to Expiry",
                    format="%d"
                ),

                "risk_status": st.column_config.TextColumn(
                    "Expiry Risk"
                ),

                "priority": st.column_config.TextColumn(
                    "Priority"
                ),

                "recommended_action": st.column_config.TextColumn(
                    "Recommended Action",
                    width="large"
                )
            }
        )


    # =================================================
    # 12. STOCK ANALYSIS
    # =================================================

    st.divider()

    st.subheader("Stock Analysis")

    if not filtered.empty:

        chart_data = (
            filtered.groupby("product_name", as_index=False)
            .agg(
                Remaining_Stock=("quantity_remaining", "sum"),
                Total_Batches=("batch_id", "count")
            )
            .sort_values(
                "Remaining_Stock",
                ascending=False
            )
            .head(10)
            .sort_values("Remaining_Stock", ascending=True)
        )

        fig = px.bar(
            chart_data,
            x="Remaining_Stock",
            y="product_name",
            orientation="h",
            text="Remaining_Stock",
            hover_data=["Total_Batches"],
            color_discrete_sequence=["#138A68"]
        )

        fig.update_traces(
            texttemplate="%{text:,.0f}",
            textposition="outside",
            cliponaxis=False,
            marker_line_width=0
        )

        # Apply chart layout first
        fig.update_layout(
            title=dict(
                text="Top 10 Products by Remaining Stock",
                font=dict(size=20, color="#142B3B")
            ),
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#FFFFFF",
            font=dict(
                family="Arial",
                size=14,
                color="#243746"
            ),
            xaxis=dict(
                title=dict(
                    text="Remaining Stock (Units)",
                    font=dict(size=14, color="#142B3B")
                ),
                tickfont=dict(size=12, color="#243746"),
                gridcolor="#E5ECE8",
                showline=True,
                linecolor="#C9D6D0",
                zeroline=False
            ),
            yaxis=dict(
                title=dict(
                    text="Product Name",
                    font=dict(size=14, color="#142B3B")
                ),
                tickfont=dict(size=13, color="#243746"),
                showgrid=False,
                automargin=True
            ),
            height=480,
            margin=dict(l=40, r=90, t=80, b=65),
            showlegend=False
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displaylogo": False,
                "responsive": True
            }
        )

        st.caption(
            f"Showing {len(chart_data)} products. "
            f"Total matching batches: {len(filtered):,}"
        )

    else:

        st.info("No matching stock records available.")

    # =================================================
    # 13. DOWNLOAD REPORT
    # =================================================

    st.divider()

    st.subheader("Export Inventory Report")

    if not filtered.empty:

        csv_data = filtered.to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            "Download Filtered Inventory CSV",
            data=csv_data,
            file_name="wastewise_inventory_report.csv",
            mime="text/csv",
            use_container_width=True
        )

    else:

        st.button(
            "Download Filtered Inventory CSV",
            disabled=True,
            use_container_width=True
        )

    show_stock_movements(data)

    st.caption(
        "WasteWise AI | Inventory data from MySQL. "
        "Expiry-risk predictions are decision-support estimates. "
        "Expired products must never be sold."
    )


# =====================================================
# STOCK MOVEMENT MANAGEMENT
# =====================================================

def calculate_stock_movement(
    previous_quantity,
    movement_type,
    quantity,
    reason,
    expiry_date=None,
    adjustment_direction="Decrease",
    today=None
):
    """Validate a stock movement and return the new stock quantity."""
    from datetime import date

    previous_quantity = int(previous_quantity)
    quantity = int(quantity)
    today = today or date.today()

    allowed_types = {"Sold", "Consumed", "Wasted", "Adjustment"}

    if movement_type not in allowed_types:
        raise ValueError("Invalid stock movement type.")

    if quantity <= 0:
        raise ValueError("Movement quantity must be greater than zero.")

    if previous_quantity < 0:
        raise ValueError("Current stock cannot be negative.")

    clean_reason = str(reason or "").strip()
    if not clean_reason:
        raise ValueError("Please enter a reason for this stock movement.")
    if len(clean_reason) > 255:
        raise ValueError("Reason must not exceed 255 characters.")

    if movement_type == "Adjustment":
        if adjustment_direction not in {"Increase", "Decrease"}:
            raise ValueError("Invalid adjustment direction.")

        if adjustment_direction == "Increase":
            return previous_quantity + quantity

    if movement_type in {"Sold", "Consumed"} and expiry_date is not None:
        if isinstance(expiry_date, str):
            expiry_date = date.fromisoformat(expiry_date)

        if expiry_date < today:
            raise ValueError(
                f"Cannot {movement_type.lower()} stock from an expired batch."
            )

    if quantity > previous_quantity:
        raise ValueError(f"Only {previous_quantity} units are available.")

    return previous_quantity - quantity


def record_stock_movement(
    batch_id,
    movement_type,
    quantity,
    reason,
    adjustment_direction="Decrease"
):
    quantity = int(quantity)

    with engine.begin() as conn:
        batch = conn.execute(
            text("""
                SELECT quantity_remaining, expiry_date
                FROM inventory_batches
                WHERE batch_id = :batch_id
                FOR UPDATE
            """),
            {"batch_id": int(batch_id)}
        ).mappings().first()

        if batch is None:
            raise ValueError("Inventory batch was not found.")

        previous_quantity = int(batch["quantity_remaining"] or 0)

        new_quantity = calculate_stock_movement(
            previous_quantity=previous_quantity,
            movement_type=movement_type,
            quantity=quantity,
            reason=reason,
            expiry_date=batch["expiry_date"],
            adjustment_direction=adjustment_direction
        )

        conn.execute(
            text("""
                UPDATE inventory_batches
                SET quantity_remaining = :new_quantity
                WHERE batch_id = :batch_id
            """),
            {
                "new_quantity": new_quantity,
                "batch_id": int(batch_id)
            }
        )

        conn.execute(
            text("""
                INSERT INTO stock_movements (
                    batch_id, movement_type, quantity,
                    previous_quantity, new_quantity, reason
                )
                VALUES (
                    :batch_id, :movement_type, :quantity,
                    :previous_quantity, :new_quantity, :reason
                )
            """),
            {
                "batch_id": int(batch_id),
                "movement_type": movement_type,
                "quantity": quantity,
                "previous_quantity": previous_quantity,
                "new_quantity": new_quantity,
                "reason": str(reason).strip()
            }
        )

    return previous_quantity, new_quantity


def show_stock_movements(data):
    st.divider()
    st.subheader("Stock Movement Management")
    st.caption("Record and track inventory stock movements.")

    if data.empty:
        st.info("No inventory batches available.")
        return

    batch_options = sorted(
        data["batch_id"].dropna().astype(int).unique().tolist(),
        reverse=True
    )

    batch_labels = {
        int(row["batch_id"]):
            f"Batch {int(row['batch_id'])} | {row['product_name']} | "
            f"Available: {int(row['quantity_remaining'])}"
        for _, row in data.drop_duplicates("batch_id").iterrows()
    }

    with st.form("stock_movement_form"):
        selected_batch = st.selectbox(
            "Select Inventory Batch",
            batch_options,
            format_func=lambda value: batch_labels.get(value, str(value))
        )

        movement_type = st.selectbox(
            "Movement Type",
            ["Sold", "Consumed", "Wasted", "Adjustment"]
        )

        adjustment_direction = st.radio(
            "Adjustment Direction",
            ["Decrease", "Increase"],
            horizontal=True
        )

        quantity = st.number_input(
            "Movement Quantity",
            min_value=1,
            value=1,
            step=1
        )

        reason = st.text_input(
            "Reason / Notes",
            placeholder="Enter movement reason"
        )

        submitted = st.form_submit_button(
            "Save Stock Movement",
            type="primary",
            use_container_width=True
        )

        if submitted:
            try:
                previous, updated = record_stock_movement(
                    selected_batch,
                    movement_type,
                    quantity,
                    reason,
                    adjustment_direction
                )
                st.success(
                    f"Movement saved. Stock: {previous} → {updated}"
                )
                st.cache_data.clear()
                st.rerun()
            except Exception as error:
                st.error(f"Unable to save movement: {error}")

    st.markdown("#### Movement History")

    with engine.connect() as conn:
        history = pd.read_sql(
            text("""
                SELECT
                    sm.movement_id,
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
                LIMIT 500
            """),
            conn
        )

    if history.empty:
        st.info("No stock movements recorded yet.")
    else:
        st.dataframe(
            history,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "Download Stock Movement History",
            data=history.to_csv(index=False).encode("utf-8"),
            file_name="wastewise_stock_movements.csv",
            mime="text/csv"
        )
