import math
import uuid
from datetime import date, datetime

import pandas as pd
import streamlit as st
from sqlalchemy import text

from src.database.connection import engine
from app.components.ui import page_header, kpi_card, empty_state


# ==========================================
# DATABASE FUNCTIONS
# ==========================================

def load_suppliers():
    query = """
        SELECT supplier_id, supplier_name
        FROM suppliers
        WHERE status = 'Active'
        ORDER BY supplier_name
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)


def load_products():
    query = """
        SELECT product_id, product_name, category,
               shelf_life_days, selling_price, unit_cost
        FROM products
        ORDER BY product_name
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)


def load_purchase_orders():
    query = """
        SELECT
            po.purchase_order_id,
            po.order_number,
            s.supplier_name,
            po.order_date,
            po.expected_delivery_date,
            po.status,
            COUNT(poi.item_id) AS total_items,
            COALESCE(SUM(poi.quantity_ordered), 0) AS total_quantity,
            COALESCE(
                SUM(poi.quantity_ordered * poi.unit_cost), 0
            ) AS order_value
        FROM purchase_orders po
        INNER JOIN suppliers s
            ON po.supplier_id = s.supplier_id
        LEFT JOIN purchase_order_items poi
            ON po.purchase_order_id = poi.purchase_order_id
        GROUP BY
            po.purchase_order_id,
            po.order_number,
            s.supplier_name,
            po.order_date,
            po.expected_delivery_date,
            po.status
        ORDER BY po.purchase_order_id DESC
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)


def load_order_items(order_id):
    query = """
        SELECT
            poi.item_id,
            poi.product_id,
            p.product_name,
            poi.quantity_ordered,
            poi.quantity_received,
            poi.unit_cost,
            (poi.quantity_ordered - poi.quantity_received)
                AS quantity_pending
        FROM purchase_order_items poi
        INNER JOIN products p
            ON poi.product_id = p.product_id
        WHERE poi.purchase_order_id = :order_id
        ORDER BY p.product_name
    """
    with engine.connect() as conn:
        return pd.read_sql(
            text(query),
            conn,
            params={"order_id": order_id}
        )


# ==========================================
# CREATE PURCHASE ORDER
# ==========================================

def create_purchase_order(
    supplier_id,
    order_date,
    expected_date,
    notes,
    order_items,
):
    order_number = (
        "PO-"
        + datetime.now().strftime("%Y%m%d-%H%M%S")
        + "-"
        + uuid.uuid4().hex[:5].upper()
    )

    with engine.begin() as conn:

        result = conn.execute(
            text("""
                INSERT INTO purchase_orders (
                    order_number,
                    supplier_id,
                    order_date,
                    expected_delivery_date,
                    status,
                    notes
                )
                VALUES (
                    :number,
                    :supplier,
                    :order_date,
                    :expected_date,
                    'Pending',
                    :notes
                )
            """),
            {
                "number": order_number,
                "supplier": supplier_id,
                "order_date": order_date,
                "expected_date": expected_date,
                "notes": notes,
            }
        )

        order_id = result.lastrowid

        for item in order_items:
            conn.execute(
                text("""
                    INSERT INTO purchase_order_items (
                        purchase_order_id,
                        product_id,
                        quantity_ordered,
                        quantity_received,
                        unit_cost
                    )
                    VALUES (
                        :order_id,
                        :product_id,
                        :quantity,
                        0,
                        :unit_cost
                    )
                """),
                {
                    "order_id": order_id,
                    "product_id": item["product_id"],
                    "quantity": item["quantity"],
                    "unit_cost": item["unit_cost"],
                }
            )

    return order_number


# ==========================================
# RECEIVE PURCHASE ORDER ITEM
# ==========================================


def receive_order_item(item_id, receive_quantity, expiry_date, request_token):
    """
    Receive stock and create its inventory, prediction and
    recommendation records in one database transaction.
    """

    from src.models.predict import predict_inventory_risk
    from src.recommendations.recommendation_engine import (
        generate_inventory_recommendations
    )

    today = date.today()

    with engine.begin() as conn:

        # Lock the purchase-order item to prevent duplicate receipt.
        item = conn.execute(
            text("""
                SELECT
                    poi.purchase_order_id,
                    poi.product_id,
                    poi.quantity_ordered,
                    poi.quantity_received,
                    poi.unit_cost,
                    p.product_name,
                    p.category,
                    p.selling_price,
                    po.status
                FROM purchase_order_items poi
                INNER JOIN products p
                    ON poi.product_id = p.product_id
                INNER JOIN purchase_orders po
                    ON poi.purchase_order_id = po.purchase_order_id
                WHERE poi.item_id = :item_id
                FOR UPDATE
            """),
            {"item_id": item_id}
        ).mappings().first()

        if item is None:
            raise ValueError("Purchase order item was not found.")

        if item["status"] in ("Received", "Cancelled"):
            raise ValueError(
                "This purchase order cannot receive more stock."
            )

        remaining = (
            int(item["quantity_ordered"])
            - int(item["quantity_received"])
        )

        if receive_quantity <= 0:
            raise ValueError(
                "Receive quantity must be greater than zero."
            )

        if receive_quantity > remaining:
            raise ValueError(
                f"Only {remaining} units are pending for this item."
            )

        if expiry_date is not None and expiry_date < today:
            raise ValueError("Expiry date cannot be in the past.")

        # Register this receipt request exactly once.
        receipt_result = conn.execute(
            text("""
                INSERT IGNORE INTO stock_receipts (
                    request_token,
                    item_id,
                    received_quantity,
                    expiry_date
                )
                VALUES (
                    :request_token,
                    :item_id,
                    :quantity,
                    :expiry_date
                )
            """),
            {
                "request_token": request_token,
                "item_id": item_id,
                "quantity": int(receive_quantity),
                "expiry_date": expiry_date,
            }
        )

        if receipt_result.rowcount != 1:
            raise ValueError(
                "This receipt request has already been processed. "
                "Refresh the page and check the purchase order."
            )

        days_to_expiry = (
            (expiry_date - today).days
            if expiry_date is not None
            else None
        )

        # Use historical average daily sales for this product.
        historical_sales = conn.execute(
            text("""
                SELECT AVG(avg_daily_sales_7d)
                FROM inventory_batches
                WHERE product_id = :product_id
                  AND avg_daily_sales_7d > 0
            """),
            {"product_id": item["product_id"]}
        ).scalar_one()

        avg_daily_sales = (
            float(historical_sales)
            if historical_sales is not None
            else None
        )

        # Expected demand is an estimate, not observed demand.
        expected_demand = (
            math.ceil(avg_daily_sales * days_to_expiry)
            if avg_daily_sales is not None and days_to_expiry is not None
            else None
        )

        inventory_surplus = (
            int(receive_quantity) - expected_demand
            if expected_demand is not None
            else None
        )

        stock_coverage = (
            int(receive_quantity) / avg_daily_sales
            if avg_daily_sales is not None and avg_daily_sales > 0
            else None
        )

        unit_price = float(item["selling_price"] or 0)
        unit_cost = float(item["unit_cost"] or 0)

        profit_per_unit = unit_price - unit_cost

        gross_margin_pct = (
            (profit_per_unit / unit_price) * 100
            if unit_price > 0
            else None
        )

        # Insert the new batch. MySQL generates its batch_id.
        insert_result = conn.execute(
            text("""
                INSERT INTO inventory_batches (
                    product_id,
                    category,
                    snapshot_date,
                    expiry_date,
                    initial_quantity,
                    quantity_remaining,
                    days_to_expiry,
                    avg_daily_sales_7d,
                    expected_demand_before_expiry,
                    inventory_surplus,
                    stock_coverage_days,
                    unit_price,
                    unit_cost,
                    discount_pct
                )
                VALUES (
                    :product_id,
                    :category,
                    :snapshot_date,
                    :expiry_date,
                    :quantity,
                    :quantity,
                    :days_to_expiry,
                    :avg_daily_sales,
                    :expected_demand,
                    :inventory_surplus,
                    :stock_coverage,
                    :unit_price,
                    :unit_cost,
                    0
                )
            """),
            {
                "product_id": item["product_id"],
                "category": item["category"],
                "snapshot_date": today,
                "expiry_date": expiry_date,
                "quantity": int(receive_quantity),
                "days_to_expiry": days_to_expiry,
                "avg_daily_sales": avg_daily_sales,
                "expected_demand": expected_demand,
                "inventory_surplus": inventory_surplus,
                "stock_coverage": stock_coverage,
                "unit_price": unit_price,
                "unit_cost": unit_cost,
            }
        )

        new_batch_id = insert_result.lastrowid

        if not new_batch_id:
            raise RuntimeError("Unable to generate a new batch ID.")

        # Link the receipt record to its inventory batch.
        conn.execute(
            text("""
                UPDATE stock_receipts
                SET batch_id = :batch_id
                WHERE request_token = :request_token
            """),
            {
                "batch_id": int(new_batch_id),
                "request_token": request_token,
            }
        )

        # Record the incoming stock movement in this transaction.
        conn.execute(
            text("""
                INSERT INTO stock_movements (
                    batch_id,
                    movement_type,
                    quantity,
                    previous_quantity,
                    new_quantity,
                    reason
                )
                VALUES (
                    :batch_id,
                    'Received',
                    :quantity,
                    0,
                    :new_quantity,
                    'Received against purchase order'
                )
            """),
            {
                "batch_id": int(new_batch_id),
                "quantity": int(receive_quantity),
                "new_quantity": int(receive_quantity),
            }
        )

        # Build every feature required by the trained model.
        batch_data = {
            "batch_id": int(new_batch_id),
            "quantity_remaining": int(receive_quantity),
            "initial_quantity": int(receive_quantity),
            "days_to_expiry": days_to_expiry,
            "avg_daily_sales_7d": avg_daily_sales,
            "expected_demand_before_expiry": expected_demand,
            "unit_price": unit_price,
            "unit_cost": unit_cost,
            "discount_pct": 0,
            "stock_coverage_days": stock_coverage,
            "remaining_stock_pct": 100.0,
            "profit_per_unit": profit_per_unit,
            "gross_margin_pct": gross_margin_pct,
        }

        inventory_df = pd.DataFrame([batch_data])

        # Generate the ML risk prediction.
        predictions_df = predict_inventory_risk(inventory_df)

        prediction = predictions_df.iloc[0]

        # Save the prediction so the dashboard can display the batch.
        conn.execute(
            text("""
                INSERT INTO predictions (
                    batch_id,
                    risk_status,
                    risk_probability
                )
                VALUES (
                    :batch_id,
                    :risk_status,
                    :risk_probability
                )
            """),
            {
                "batch_id": int(new_batch_id),
                "risk_status": str(prediction["risk_status"]),
                "risk_probability": (
                    None
                    if pd.isna(prediction["risk_probability"])
                    else float(prediction["risk_probability"])
                ),
            }
        )

        # Generate the inventory recommendation.
        recommendation_input = pd.DataFrame([{
            "batch_id": int(new_batch_id),
            "product_name": item["product_name"],
            "days_to_expiry": days_to_expiry,
            "quantity_remaining": int(receive_quantity),
            "inventory_surplus": inventory_surplus,
        }])

        recommendations_df = generate_inventory_recommendations(
            recommendation_input,
            predictions_df
        )

        recommendation = recommendations_df.iloc[0]

        conn.execute(
            text("""
                INSERT INTO recommendations (
                    batch_id,
                    priority,
                    recommended_action
                )
                VALUES (
                    :batch_id,
                    :priority,
                    :action
                )
            """),
            {
                "batch_id": int(new_batch_id),
                "priority": str(recommendation["priority"]),
                "action": str(recommendation["recommended_action"]),
            }
        )

        # Update the received quantity only after all ML records exist.
        new_received = (
            int(item["quantity_received"]) + int(receive_quantity)
        )

        conn.execute(
            text("""
                UPDATE purchase_order_items
                SET quantity_received = :received
                WHERE item_id = :item_id
            """),
            {
                "received": new_received,
                "item_id": item_id,
            }
        )

        pending_count = conn.execute(
            text("""
                SELECT COUNT(*)
                FROM purchase_order_items
                WHERE purchase_order_id = :order_id
                  AND quantity_received < quantity_ordered
            """),
            {"order_id": item["purchase_order_id"]}
        ).scalar_one()

        new_status = (
            "Partially Received"
            if pending_count > 0
            else "Received"
        )

        conn.execute(
            text("""
                UPDATE purchase_orders
                SET status = :status
                WHERE purchase_order_id = :order_id
            """),
            {
                "status": new_status,
                "order_id": item["purchase_order_id"],
            }
        )

    return new_status


# ==========================================
# STREAMLIT PAGE
# ==========================================

def show_purchase_orders():

    page_header(
        "Incoming Stock & Purchase Orders",
        "Create orders, track deliveries and receive stock into inventory."
    )

    try:
        suppliers = load_suppliers()
        products = load_products()
        orders = load_purchase_orders()

    except Exception as error:
        st.error(f"Unable to load purchase order data: {error}")
        return

    total_orders = len(orders)

    pending_orders = (
        orders["status"] == "Pending"
    ).sum() if not orders.empty else 0

    partial_orders = (
        orders["status"] == "Partially Received"
    ).sum() if not orders.empty else 0

    received_orders = (
        orders["status"] == "Received"
    ).sum() if not orders.empty else 0

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        kpi_card("Total Orders", f"{total_orders:,}")

    with c2:
        kpi_card("Pending Orders", f"{pending_orders:,}")

    with c3:
        kpi_card("Partially Received", f"{partial_orders:,}")

    with c4:
        kpi_card("Completed Orders", f"{received_orders:,}")

    st.divider()

    create_tab, receive_tab, history_tab = st.tabs(
        [
            "Create Purchase Order",
            "Receive Stock",
            "Order History",
        ]
    )

    # ======================================
    # CREATE ORDER TAB
    # ======================================

    with create_tab:

        st.subheader("Create New Purchase Order")

        if suppliers.empty:
            st.warning(
                "No active suppliers found. Add a supplier first "
                "from the Suppliers page."
            )

        elif products.empty:
            st.warning("No products are available.")

        else:

            supplier_map = {
                f"{row.supplier_name} (ID: {row.supplier_id})":
                    int(row.supplier_id)
                for row in suppliers.itertuples()
            }

            product_map = {
                f"{row.product_name} (ID: {row.product_id})":
                    row
                for row in products.itertuples()
            }

            selected_supplier = st.selectbox(
                "Select Supplier",
                list(supplier_map.keys()),
                key="po_supplier",
            )

            order_date = st.date_input(
                "Order Date",
                value=date.today(),
                key="po_order_date",
            )

            expected_date = st.date_input(
                "Expected Delivery Date",
                value=date.today(),
                key="po_expected_date",
            )

            selected_products = st.multiselect(
                "Select Products",
                list(product_map.keys()),
                key="po_products",
                help="Select one or more products for this order.",
            )

            order_items = []

            if selected_products:

                st.markdown("#### Product Quantities and Costs")

                for index, product_label in enumerate(selected_products):

                    product = product_map[product_label]

                    with st.container(border=True):

                        st.markdown(f"**{product.product_name}**")

                        col1, col2 = st.columns(2)

                        with col1:
                            quantity = st.number_input(
                                "Quantity",
                                min_value=1,
                                value=1,
                                step=1,
                                key=f"po_qty_{product.product_id}",
                            )

                        with col2:
                            default_cost = float(
                                product.unit_cost or 0
                            )

                            unit_cost = st.number_input(
                                "Unit Cost (₹)",
                                min_value=0.01,
                                value=max(default_cost, 0.01),
                                step=1.0,
                                key=f"po_cost_{product.product_id}",
                            )

                    order_items.append({
                        "product_id": int(product.product_id),
                        "quantity": int(quantity),
                        "unit_cost": float(unit_cost),
                    })

            notes = st.text_area(
                "Order Notes",
                key="po_notes",
                placeholder="Optional order instructions..."
            )

            order_total = sum(
                item["quantity"] * item["unit_cost"]
                for item in order_items
            )

            st.metric(
                "Estimated Purchase Order Value",
                f"₹{order_total:,.2f}"
            )

            if st.button(
                "Create Purchase Order",
                type="primary",
                use_container_width=True,
                disabled=not order_items,
            ):

                if expected_date < order_date:
                    st.error(
                        "Expected delivery date cannot be before "
                        "the order date."
                    )

                else:
                    try:
                        order_number = create_purchase_order(
                            supplier_id=supplier_map[selected_supplier],
                            order_date=order_date,
                            expected_date=expected_date,
                            notes=notes.strip(),
                            order_items=order_items,
                        )

                        st.success(
                            f"Purchase order {order_number} created successfully."
                        )
                        st.rerun()

                    except Exception as error:
                        st.error(f"Unable to create order: {error}")

    # ======================================
    # RECEIVE STOCK TAB
    # ======================================

    with receive_tab:

        st.subheader("Receive Incoming Stock")

        receivable = orders[
            orders["status"].isin([
                "Pending",
                "Partially Received",
            ])
        ].copy()

        if receivable.empty:
            st.info("There are no pending deliveries to receive.")

        else:

            order_map = {
                f"{row.order_number} | {row.supplier_name} | {row.status}":
                    int(row.purchase_order_id)
                for row in receivable.itertuples()
            }

            selected_order = st.selectbox(
                "Select Purchase Order",
                list(order_map.keys()),
                key="receive_order",
            )

            order_id = order_map[selected_order]

            items = load_order_items(order_id)

            if items.empty:
                st.info("This purchase order has no items.")

            else:

                item_map = {
                    (
                        f"{row.product_name} | "
                        f"Pending: {int(row.quantity_pending)}"
                    ): int(row.item_id)
                    for row in items.itertuples()
                    if row.quantity_pending > 0
                }

                if not item_map:
                    st.success("All items in this order are received.")

                else:

                    selected_item_label = st.selectbox(
                        "Select Product to Receive",
                        list(item_map.keys()),
                        key="receive_item",
                    )

                    selected_item_id = item_map[
                        selected_item_label
                    ]

                    selected_item = items[
                        items["item_id"] == selected_item_id
                    ].iloc[0]

                    st.info(
                        f"Ordered: {int(selected_item['quantity_ordered'])} | "
                        f"Already Received: "
                        f"{int(selected_item['quantity_received'])} | "
                        f"Remaining: "
                        f"{int(selected_item['quantity_pending'])}"
                    )

                    receipt_token_key = (
                        f"receipt_request_token_{selected_item_id}"
                    )
                    st.session_state.setdefault(
                        receipt_token_key,
                        uuid.uuid4().hex
                    )
                    request_token = st.session_state[receipt_token_key]

                    expiry_status = st.radio(
                        "Expiry Date Status",
                        [
                            "I have verified the date on packaging",
                            "Expiry date is unknown",
                        ],
                        horizontal=True,
                        key=f"expiry_status_{selected_item_id}",
                    )

                    with st.form("receive_stock_form"):

                        receive_quantity = st.number_input(
                            "Quantity Received",
                            min_value=1,
                            max_value=int(
                                selected_item["quantity_pending"]
                            ),
                            value=1,
                            step=1,
                        )

                        if expiry_status == "Expiry date is unknown":
                            expiry_date = None
                            st.info(
                                "This batch will be marked for review "
                                "because its expiry date is unknown."
                            )
                        else:
                            expiry_date = st.date_input(
                                "Expiry Date for This Batch",
                                value=date.today(),
                                                   help="Enter the verified date printed on the packaging.",
                            )

                        submitted = st.form_submit_button(
                            "Confirm Receipt & Add Inventory Batch",
                            use_container_width=True,
                        )

                        if submitted:

                            try:
                                new_status = receive_order_item(
                                    item_id=selected_item_id,
                                    receive_quantity=int(receive_quantity),
                                    expiry_date=expiry_date,
                                    request_token=request_token,
                                )

                                # Use a fresh token for the next receipt.
                                st.session_state[receipt_token_key] = (
                                    uuid.uuid4().hex
                                )

                                st.success(
                                    "Stock received successfully. "
                                    "A separate inventory batch was created. "
                                    f"Order status: {new_status}"
                                )
                                st.cache_data.clear()
                                st.rerun()

                            except Exception as error:
                                st.error(
                                    f"Unable to receive stock: {error}"
                                )

    # ======================================
    # ORDER HISTORY TAB
    # ======================================

    with history_tab:

        st.subheader("Purchase Order History")

        if orders.empty:
            empty_state(
                "No purchase orders yet",
                "Create your first purchase order to get started."
            )

        else:

            status_filter = st.selectbox(
                "Filter by Status",
                [
                    "All",
                    "Pending",
                    "Partially Received",
                    "Received",
                ],
                key="po_history_status",
            )

            filtered = orders.copy()

            if status_filter != "All":
                filtered = filtered[
                    filtered["status"] == status_filter
                ]

            st.dataframe(
                filtered,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "purchase_order_id": "Order ID",
                    "order_number": "Order Number",
                    "supplier_name": "Supplier",
                    "order_date": "Order Date",
                    "expected_delivery_date": "Expected Delivery",
                    "status": "Status",
                    "total_items": "Products",
                    "total_quantity": "Ordered Units",
                    "order_value": st.column_config.NumberColumn(
                        "Order Value",
                        format="₹%.2f",
                    ),
                },
            )

            st.download_button(
                "Download Purchase Order History",
                data=filtered.to_csv(index=False).encode("utf-8"),
                file_name="wastewise_purchase_orders.csv",
                mime="text/csv",
                use_container_width=True,
            )
