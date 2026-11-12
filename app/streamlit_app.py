import streamlit as st

from app.components.ui import load_theme, app_footer
from app.components.data_service import load_inventory_data
from app.components.dashboard_view import show_dashboard
from app.components.products_view import show_products
from app.components.inventory_view import show_inventory
from app.components.suppliers_view import show_suppliers
from app.components.purchase_orders_view import show_purchase_orders
from app.components.sales_analytics_view import show_sales_analytics
from app.components.reorder_planning_view import show_reorder_planning
from app.components.demand_forecast_view import show_demand_forecasts
from app.components.recommendations_view import show_recommendations
from app.monitoring_dashboard import show_model_monitoring
from app.components.settings_view import show_settings
from app.components.waste_insights_view import show_waste_insights


# ==========================================
# PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="WasteWise AI | Inventory Management",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_theme()


# ==========================================
# DATABASE DATA
# ==========================================

@st.cache_data(ttl=60)
def get_data():
    return load_inventory_data()


try:
    df = get_data()
    database_connected = True

except Exception as error:
    database_connected = False
    df = None
    database_error = str(error)


# ==========================================
# 13 APPLICATION MODULES
# ==========================================

pages = [
    "Dashboard",
    "Products",
    "Inventory",
    "Incoming Stock & Purchase Orders",
    "Suppliers",
    "Sales Analytics",
    "Demand Forecasts",
    "Reorder Planning",
    "Expiry Tracking",
    "Recommendations",
    "Waste Insights",
    "Model Monitoring",
    "Settings",
]


page_descriptions = {
    "Incoming Stock & Purchase Orders":
        "Manage incoming inventory and purchase orders.",

    "Suppliers":
        "Manage supplier information and supplier relationships.",

    "Sales Analytics":
        "Analyze sales performance and product demand.",

    "Demand Forecasts":
        "Forecast future product demand using available sales history.",

    "Reorder Planning":
        "Identify products that may require replenishment.",

    "Expiry Tracking":
        "Track expired products and upcoming expiry dates.",

    "Recommendations":
        "Review inventory optimization recommendations.",

    "Waste Insights":
        "Analyze inventory surplus, expiry risk and potential waste.",

    "Model Monitoring":
        "Review machine learning performance and monitoring reports.",

    "Settings":
        "Manage application information and database settings.",
}


# ==========================================
# SIDEBAR NAVIGATION
# ==========================================

with st.sidebar:

    st.markdown(
        """
        <div style="padding:12px 0 18px;">
            <h2 style="color:#35C99A;margin:0;font-size:24px;">
                ♻️ WasteWise AI
            </h2>
            <p style="color:#A6B5BF;font-size:11px;letter-spacing:1px;">
                FRESHNESS INTELLIGENCE
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    st.markdown("### NAVIGATION")

    selected_page = st.radio(
        "Select Module",
        pages,
        index=0,
        label_visibility="collapsed",
        key="ww_navigation",
    )

    st.divider()

    st.markdown("### DATABASE STATUS")

    if database_connected:
        st.success("MySQL Connected")
        st.caption("Database: wastewise_ai")
        st.caption(f"Inventory Records: {len(df):,}")

    else:
        st.error("MySQL Disconnected")
        st.caption("Check your database configuration.")

    if st.button(
        "↻ Refresh Database Data",
        use_container_width=True,
    ):
        st.cache_data.clear()
        st.rerun()

    st.divider()

    st.caption("WasteWise AI | Version 1.0")
    st.caption("Smart Inventory Management")


# ==========================================
# DATABASE ERROR HANDLING
# ==========================================

if not database_connected:

    st.error("Unable to load the MySQL database.")

    with st.expander("View technical error"):
        st.code(database_error)

    st.info(
        "Check that MySQL is running and your existing "
        "database configuration is correct."
    )

    st.stop()


# ==========================================
# PAGE ROUTING
# ==========================================

if selected_page == "Dashboard":

    show_dashboard(df)


elif selected_page == "Products":

    show_products()


elif selected_page == "Inventory":

    show_inventory(df)


elif selected_page == "Suppliers":

    show_suppliers()


elif selected_page == "Incoming Stock & Purchase Orders":

    show_purchase_orders()


elif selected_page == "Recommendations":

    show_recommendations(df)


elif selected_page == "Expiry Tracking":

    st.title("Expiry Tracking")
    st.caption(page_descriptions[selected_page])

    if "days_to_expiry" in df.columns:

        expiry_data = df.copy()

        expiry_data["days_to_expiry"] = (
            expiry_data["days_to_expiry"]
            .apply(lambda x: float(x) if x is not None else None)
        )

        expired = expiry_data[
            expiry_data["risk_status"] == "Expired"
        ]

        today = expiry_data[
            expiry_data["risk_status"]
            == "Expires Today - Immediate Review"
        ]

        upcoming = expiry_data[
            expiry_data["days_to_expiry"].between(1, 7)
        ]

        c1, c2, c3 = st.columns(3)

        c1.metric("Expired Batches", f"{len(expired):,}")
        c2.metric("Expiring Today", f"{len(today):,}")
        c3.metric("Expiring in 7 Days", f"{len(upcoming):,}")

        st.subheader("Expiry Attention Required")

        expiry_table = expiry_data[
            expiry_data["days_to_expiry"].notna()
        ].sort_values("days_to_expiry")

        st.dataframe(
            expiry_table[
                [
                    "batch_id",
                    "product_name",
                    "days_to_expiry",
                    "risk_status",
                    "recommended_action",
                ]
            ].head(100),
            use_container_width=True,
            hide_index=True,
        )

    else:
        st.warning("Expiry information is unavailable.")


elif selected_page == "Demand Forecasts":

    show_demand_forecasts(df)


elif selected_page == "Reorder Planning":

    show_reorder_planning(df)


elif selected_page == "Sales Analytics":

    show_sales_analytics(df)


elif selected_page == "Waste Insights":

    show_waste_insights(df)


elif selected_page == "Model Monitoring":

    show_model_monitoring()


elif selected_page == "Settings":

    show_settings()

else:

    st.title(selected_page)
    st.caption(page_descriptions[selected_page])

    st.info(
        "This module is registered in the application navigation. "
        "Its complete functionality will be implemented using "
        "verified database records and existing project services."
    )


# ==========================================
# APPLICATION FOOTER
# ==========================================

app_footer()
