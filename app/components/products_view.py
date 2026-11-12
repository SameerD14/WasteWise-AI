import streamlit as st
import pandas as pd

from sqlalchemy import text
from src.database.connection import engine


# ==========================================
# PAGE CONFIGURATION
# ==========================================

def show_products():

    st.title("Product Management")

    st.caption(
        "Manage your product catalogue, categories, "
        "selling prices and shelf life."
    )

    # ======================================
    # LOAD PRODUCTS FROM MYSQL
    # ======================================

    def get_products():

        query = """
        SELECT
            product_id,
            product_name,
            category,
            shelf_life_days,
            selling_price,
            unit_cost
        FROM products
        ORDER BY product_id
        """

        with engine.connect() as connection:
            return pd.read_sql(text(query), connection)

    try:
        products = get_products()

    except Exception as error:
        st.error(f"Unable to load products: {error}")
        return

    # ======================================
    # KPI CARDS
    # ======================================

    total_products = len(products)

    total_categories = products["category"].nunique()

    average_price = (
        products["selling_price"].mean()
        if not products.empty else 0
    )

    c1, c2, c3 = st.columns(3)

    c1.metric("Total Products", f"{total_products:,}")
    c2.metric("Product Categories", f"{total_categories:,}")
    c3.metric("Average Selling Price", f"₹{average_price:,.2f}")

    st.divider()

    # ======================================
    # PRODUCT CATALOGUE
    # ======================================

    st.subheader("Product Catalogue")

    search_col, category_col = st.columns([2, 1])

    with search_col:
        search = st.text_input(
            "Search Products",
            placeholder="Search by product name..."
        )

    categories = sorted(
        products["category"].dropna().astype(str).unique().tolist()
    )

    with category_col:
        selected_category = st.selectbox(
            "Filter by Category",
            ["All Categories"] + categories
        )

    display_products = products.copy()

    if search:
        display_products = display_products[
            display_products["product_name"].str.contains(
                search, case=False, na=False
            )
        ]

    if selected_category != "All Categories":
        display_products = display_products[
            display_products["category"] == selected_category
        ]

    if display_products.empty:
        st.info("No matching products found.")
    else:
        st.dataframe(
            display_products,
            use_container_width=True,
            hide_index=True,
            height=350,
            column_config={
                "product_id": st.column_config.NumberColumn("Product ID"),
                "product_name": st.column_config.TextColumn("Product Name"),
                "category": st.column_config.TextColumn("Category"),
                "shelf_life_days": st.column_config.NumberColumn(
                    "Shelf Life (Days)"
                ),
                "selling_price": st.column_config.NumberColumn(
                    "Selling Price (₹)", format="₹%.2f"
                ),
                "unit_cost": st.column_config.NumberColumn(
                    "Unit Cost (₹)", format="₹%.2f"
                )
            }
        )

    st.caption(
        f"Showing {len(display_products)} of {total_products} products."
    )

    st.divider()

    # ======================================
    # ADD / EDIT / DELETE TABS
    # ======================================

    add_tab, edit_tab, delete_tab = st.tabs(
        ["＋ Add Product", "✏️ Edit Product", "🗑️ Delete Product"]
    )

    # ======================================
    # ADD PRODUCT
    # ======================================

    with add_tab:

        st.subheader("Add New Product")

        with st.form("add_product_form"):

            name = st.text_input(
                "Product Name",
                placeholder="Example: Fresh Milk 1L"
            )

            existing_categories = sorted(
                products["category"].dropna().astype(str).unique().tolist()
            )

            category_choice = st.selectbox(
                "Select Category",
                existing_categories + ["Other / New Category"]
            )

            if category_choice == "Other / New Category":
                category = st.text_input(
                    "Enter New Category",
                    placeholder="Example: Frozen Food"
                )
            else:
                category = category_choice

            col1, col2, col3 = st.columns(3)

            with col1:
                shelf_life = st.number_input(
                    "Shelf Life (Days)",
                    min_value=1,
                    value=7,
                    step=1
                )

            with col2:
                selling_price = st.number_input(
                    "Selling Price (₹)",
                    min_value=0.01,
                    value=100.0,
                    step=1.0
                )

            with col3:
                unit_cost = st.number_input(
                    "Unit Cost (₹)",
                    min_value=0.01,
                    value=50.0,
                    step=1.0
                )

            submitted = st.form_submit_button(
                "＋ Add Product",
                use_container_width=True
            )

            if submitted:

                if not name.strip():
                    st.error("Please enter a product name.")

                elif not category.strip():
                    st.error("Please select or enter a category.")

                elif unit_cost > selling_price:
                    st.error(
                        "Unit cost cannot be greater than selling price."
                    )

                elif (
                    not products.empty
                    and products["product_name"].str.strip().str.lower()
                    .eq(name.strip().lower()).any()
                ):
                    st.error("This product already exists.")

                else:

                    try:
                        with engine.begin() as connection:

                            next_id = connection.execute(
                                text(
                                    "SELECT COALESCE(MAX(product_id), 0) + 1 "
                                    "FROM products"
                                )
                            ).scalar_one()

                            connection.execute(
                                text("""
                                    INSERT INTO products (
                                        product_id,
                                        product_name,
                                        category,
                                        shelf_life_days,
                                        selling_price,
                                        unit_cost
                                    )
                                    VALUES (
                                        :product_id,
                                        :product_name,
                                        :category,
                                        :shelf_life_days,
                                        :selling_price,
                                        :unit_cost
                                    )
                                """),
                                {
                                    "product_id": next_id,
                                    "product_name": name.strip(),
                                    "category": category.strip(),
                                    "shelf_life_days": shelf_life,
                                    "selling_price": selling_price,
                                    "unit_cost": unit_cost
                                }
                            )

                        st.cache_data.clear()
                        st.success(
                            f"Product added successfully! ID: {next_id}"
                        )
                        st.rerun()

                    except Exception as error:
                        st.error(f"Unable to add product: {error}")

    # ======================================
    # EDIT PRODUCT
    # ======================================

    with edit_tab:

        st.subheader("Update Product Information")

        if products.empty:

            st.info("No products available to edit.")

        else:

            product_options = {
                f"{row.product_name} (ID: {row.product_id})":
                int(row.product_id)
                for row in products.itertuples()
            }

            selected_label = st.selectbox(
                "Select Product to Edit",
                list(product_options.keys()),
                key="edit_product_selection"
            )

            selected_id = product_options[selected_label]

            selected_row = products[
                products["product_id"] == selected_id
            ].iloc[0]

            edit_categories = sorted(
                products["category"].dropna().astype(str).unique().tolist()
            )

            current_category = str(selected_row["category"])

            if current_category not in edit_categories:
                edit_categories.append(current_category)

            with st.form("edit_product_form"):

                edit_name = st.text_input(
                    "Product Name",
                    value=str(selected_row["product_name"])
                )

                edit_category = st.selectbox(
                    "Category",
                    edit_categories,
                    index=edit_categories.index(current_category)
                )

                col1, col2, col3 = st.columns(3)

                with col1:
                    edit_shelf = st.number_input(
                        "Shelf Life (Days)",
                        min_value=1,
                        value=max(1, int(selected_row["shelf_life_days"] or 1))
                    )

                with col2:
                    edit_price = st.number_input(
                        "Selling Price (₹)",
                        min_value=0.01,
                        value=max(0.01, float(selected_row["selling_price"] or 0.01))
                    )

                with col3:
                    edit_cost = st.number_input(
                        "Unit Cost (₹)",
                        min_value=0.01,
                        value=max(0.01, float(selected_row["unit_cost"] or 0.01))
                    )

                update = st.form_submit_button(
                    "Save Changes",
                    use_container_width=True
                )

                if update:

                    if not edit_name.strip():
                        st.error("Product name cannot be empty.")

                    elif edit_cost > edit_price:
                        st.error(
                            "Unit cost cannot be greater than selling price."
                        )

                    else:

                        try:
                            with engine.begin() as connection:

                                connection.execute(
                                    text("""
                                        UPDATE products
                                        SET
                                            product_name = :name,
                                            category = :category,
                                            shelf_life_days = :shelf,
                                            selling_price = :price,
                                            unit_cost = :cost
                                        WHERE product_id = :product_id
                                    """),
                                    {
                                        "name": edit_name.strip(),
                                        "category": edit_category,
                                        "shelf": edit_shelf,
                                        "price": edit_price,
                                        "cost": edit_cost,
                                        "product_id": selected_id
                                    }
                                )

                            st.cache_data.clear()
                            st.success("Product updated successfully.")
                            st.rerun()

                        except Exception as error:
                            st.error(f"Unable to update product: {error}")

    # ======================================
    # DELETE PRODUCT
    # ======================================

    with delete_tab:

        st.subheader("Delete Product")

        st.warning(
            "Deleting a product may fail if inventory batches "
            "are linked to it. Existing inventory records are protected "
            "by database foreign-key constraints."
        )

        if products.empty:

            st.info("No products available.")

        else:

            delete_options = {
                f"{row.product_name} (ID: {row.product_id})":
                int(row.product_id)
                for row in products.itertuples()
            }

            delete_label = st.selectbox(
                "Select Product to Delete",
                list(delete_options.keys()),
                key="delete_product_selection"
            )

            delete_id = delete_options[delete_label]

            confirm = st.checkbox(
                "I confirm that I want to delete this product."
            )

            if st.button(
                "Delete Selected Product",
                type="primary",
                disabled=not confirm,
                use_container_width=True
            ):

                try:
                    with engine.begin() as connection:

                        connection.execute(
                            text("""
                                DELETE FROM products
                                WHERE product_id = :product_id
                            """),
                            {"product_id": delete_id}
                        )

                    st.cache_data.clear()
                    st.success("Product deleted successfully.")
                    st.rerun()

                except Exception:
                    st.error(
                        "This product cannot be deleted because it may "
                        "be linked to existing inventory records. "
                        "Remove or reassign dependent records first."
                    )

    # ======================================
    # FOOTER
    # ======================================

    st.divider()

    st.caption(
        "WasteWise AI | Product Catalogue Management | MySQL"
    )
