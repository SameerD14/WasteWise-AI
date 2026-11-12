import re
import pandas as pd
import streamlit as st
from sqlalchemy import text

from src.database.connection import engine
from app.components.ui import page_header, kpi_card, empty_state


# ------------------------------------------
# DATABASE
# ------------------------------------------

def load_suppliers():
    query = """
        SELECT supplier_id, supplier_name, contact_person,
               email, phone, address, city, status, created_at
        FROM suppliers
        ORDER BY supplier_name
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)


def valid_email(email):
    if not email:
        return True
    return re.fullmatch(
        r"[^@\s]+@[^@\s]+\.[^@\s]+", email
    ) is not None


def insert_supplier(name, contact, email, phone, city, address):
    with engine.begin() as conn:
        duplicate = conn.execute(
            text("""
                SELECT supplier_id
                FROM suppliers
                WHERE LOWER(TRIM(supplier_name)) = LOWER(:name)
                LIMIT 1
            """),
            {"name": name}
        ).first()

        if duplicate:
            raise ValueError(
                "A supplier with this name already exists."
            )

        result = conn.execute(
            text("""
                INSERT INTO suppliers (
                    supplier_name,
                    contact_person,
                    email,
                    phone,
                    address,
                    city,
                    status
                )
                VALUES (
                    :name,
                    :contact,
                    :email,
                    :phone,
                    :address,
                    :city,
                    'Active'
                )
            """),
            {
                "name": name,
                "contact": contact or None,
                "email": email or None,
                "phone": phone or None,
                "address": address or None,
                "city": city or None,
            }
        )

        return result.lastrowid


# ------------------------------------------
# SUPPLIER PAGE
# ------------------------------------------

def show_suppliers():

    page_header(
        "Suppliers",
        "Manage supplier information and supplier relationships."
    )

    try:
        suppliers = load_suppliers()
    except Exception as error:
        st.error(f"Unable to load suppliers: {error}")
        return

    total = len(suppliers)
    active = int((suppliers["status"] == "Active").sum())
    inactive = int((suppliers["status"] == "Inactive").sum())

    c1, c2, c3 = st.columns(3)

    with c1:
        kpi_card("Total Suppliers", f"{total:,}")
    with c2:
        kpi_card("Active Suppliers", f"{active:,}")
    with c3:
        kpi_card("Inactive Suppliers", f"{inactive:,}")

    st.divider()

    add_tab, manage_tab = st.tabs(
        ["Add Supplier", "Manage Suppliers"]
    )

    # --------------------------------------
    # ADD SUPPLIER
    # --------------------------------------

    with add_tab:

        st.subheader("Register New Supplier")

        with st.form("add_supplier_form"):

            name = st.text_input(
                "Supplier Name *",
                placeholder="Enter supplier business name"
            )

            contact = st.text_input(
                "Contact Person",
                placeholder="Enter contact person's name"
            )

            email = st.text_input(
                "Email Address",
                placeholder="example@email.com"
            )

            phone = st.text_input(
                "Phone Number",
                placeholder="Enter phone number"
            )

            city = st.text_input(
                "City",
                placeholder="Enter city"
            )

            address = st.text_area(
                "Address",
                placeholder="Enter supplier address"
            )

            submitted = st.form_submit_button(
                "Save Supplier",
                type="primary",
                use_container_width=True
            )

        if submitted:

            name = name.strip()
            contact = contact.strip()
            email = email.strip()
            phone = phone.strip()
            city = city.strip()
            address = address.strip()

            if not name:
                st.error("Supplier name is required.")

            elif not valid_email(email):
                st.error("Please enter a valid email address.")

            else:
                try:
                    new_id = insert_supplier(
                        name,
                        contact,
                        email,
                        phone,
                        city,
                        address
                    )

                    st.success(
                        f"Supplier saved successfully! Supplier ID: {new_id}"
                    )
                    st.cache_data.clear()
                    st.rerun()

                except ValueError as error:
                    st.error(str(error))

                except Exception as error:
                    st.error(
                        f"Database could not save the supplier: {error}"
                    )

    # --------------------------------------
    # MANAGE SUPPLIERS
    # --------------------------------------

    with manage_tab:

        st.subheader("Supplier Directory")

        try:
            suppliers = load_suppliers()
        except Exception as error:
            st.error(f"Unable to refresh suppliers: {error}")
            return

        search = st.text_input(
            "Search Supplier",
            placeholder="Search by supplier or contact person"
        )

        status_filter = st.selectbox(
            "Supplier Status",
            ["All", "Active", "Inactive"]
        )

        filtered = suppliers.copy()

        if search:
            mask = (
                filtered["supplier_name"].fillna("").str.contains(
                    search, case=False, regex=False
                )
                |
                filtered["contact_person"].fillna("").str.contains(
                    search, case=False, regex=False
                )
            )
            filtered = filtered[mask]

        if status_filter != "All":
            filtered = filtered[
                filtered["status"] == status_filter
            ]

        if filtered.empty:
            empty_state(
                "No suppliers found",
                "Try another search or register a supplier."
            )
        else:
            st.dataframe(
                filtered[
                    [
                        "supplier_id",
                        "supplier_name",
                        "contact_person",
                        "email",
                        "phone",
                        "city",
                        "status"
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )

        st.divider()
        st.subheader("Edit or Change Supplier Status")

        if suppliers.empty:
            st.info("Register a supplier before using this section.")

        else:

            supplier_options = {
                f"{row.supplier_name} (ID: {row.supplier_id})":
                    int(row.supplier_id)
                for row in suppliers.itertuples()
            }

            selected_label = st.selectbox(
                "Select Supplier",
                list(supplier_options.keys()),
                key="manage_supplier_selection"
            )

            selected_id = supplier_options[selected_label]

            selected = suppliers[
                suppliers["supplier_id"] == selected_id
            ].iloc[0]

            with st.form("edit_supplier_form"):

                edit_name = st.text_input(
                    "Supplier Name",
                    value=selected["supplier_name"] or ""
                )

                edit_contact = st.text_input(
                    "Contact Person",
                    value=selected["contact_person"] or ""
                )

                edit_email = st.text_input(
                    "Email Address",
                    value=selected["email"] or ""
                )

                edit_phone = st.text_input(
                    "Phone Number",
                    value=selected["phone"] or ""
                )

                edit_city = st.text_input(
                    "City",
                    value=selected["city"] or ""
                )

                edit_address = st.text_area(
                    "Address",
                    value=selected["address"] or ""
                )

                update = st.form_submit_button(
                    "Update Supplier",
                    use_container_width=True
                )

            if update:

                edit_name = edit_name.strip()
                edit_email = edit_email.strip()

                if not edit_name:
                    st.error("Supplier name is required.")

                elif not valid_email(edit_email):
                    st.error("Please enter a valid email address.")

                else:
                    try:
                        with engine.begin() as conn:

                            duplicate = conn.execute(
                                text("""
                                    SELECT supplier_id
                                    FROM suppliers
                                    WHERE LOWER(TRIM(supplier_name)) =
                                          LOWER(:name)
                                      AND supplier_id != :id
                                    LIMIT 1
                                """),
                                {
                                    "name": edit_name,
                                    "id": selected_id
                                }
                            ).first()

                            if duplicate:
                                raise ValueError(
                                    "Another supplier already uses this name."
                                )

                            conn.execute(
                                text("""
                                    UPDATE suppliers
                                    SET supplier_name = :name,
                                        contact_person = :contact,
                                        email = :email,
                                        phone = :phone,
                                        city = :city,
                                        address = :address
                                    WHERE supplier_id = :id
                                """),
                                {
                                    "name": edit_name,
                                    "contact": edit_contact.strip(),
                                    "email": edit_email or None,
                                    "phone": edit_phone.strip() or None,
                                    "city": edit_city.strip() or None,
                                    "address": edit_address.strip() or None,
                                    "id": selected_id
                                }
                            )

                        st.success("Supplier updated successfully.")
                        st.rerun()

                    except ValueError as error:
                        st.error(str(error))

                    except Exception as error:
                        st.error(f"Update failed: {error}")

            current_status = selected["status"]

            if current_status == "Active":

                if st.button(
                    "Deactivate Selected Supplier",
                    key="deactivate_supplier"
                ):
                    try:
                        with engine.begin() as conn:
                            conn.execute(
                                text("""
                                    UPDATE suppliers
                                    SET status = 'Inactive'
                                    WHERE supplier_id = :id
                                """),
                                {"id": selected_id}
                            )

                        st.success("Supplier deactivated.")
                        st.rerun()

                    except Exception as error:
                        st.error(f"Unable to deactivate supplier: {error}")

            else:

                if st.button(
                    "Reactivate Selected Supplier",
                    key="reactivate_supplier"
                ):
                    try:
                        with engine.begin() as conn:
                            conn.execute(
                                text("""
                                    UPDATE suppliers
                                    SET status = 'Active'
                                    WHERE supplier_id = :id
                                """),
                                {"id": selected_id}
                            )

                        st.success("Supplier reactivated.")
                        st.rerun()

                    except Exception as error:
                        st.error(f"Unable to reactivate supplier: {error}")
