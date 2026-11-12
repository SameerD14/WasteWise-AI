from sqlalchemy import text
from src.database.connection import engine

TABLES = [
    """
    CREATE TABLE IF NOT EXISTS suppliers (
        supplier_id INT AUTO_INCREMENT PRIMARY KEY,
        supplier_name VARCHAR(150) NOT NULL,
        contact_person VARCHAR(100),
        email VARCHAR(150),
        phone VARCHAR(30),
        address TEXT,
        city VARCHAR(100),
        status VARCHAR(20) NOT NULL DEFAULT 'Active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_supplier_name (supplier_name),
        INDEX idx_supplier_status (status)
    ) ENGINE=InnoDB
    """,
    """
    CREATE TABLE IF NOT EXISTS purchase_orders (
        purchase_order_id INT AUTO_INCREMENT PRIMARY KEY,
        order_number VARCHAR(40) NOT NULL UNIQUE,
        supplier_id INT NOT NULL,
        order_date DATE NOT NULL,
        expected_delivery_date DATE,
        status VARCHAR(30) NOT NULL DEFAULT 'Pending',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ON UPDATE CURRENT_TIMESTAMP,
        CONSTRAINT fk_po_supplier
            FOREIGN KEY (supplier_id)
            REFERENCES suppliers(supplier_id),
        INDEX idx_po_status (status),
        INDEX idx_po_order_date (order_date)
    ) ENGINE=InnoDB
    """,
    """
    CREATE TABLE IF NOT EXISTS purchase_order_items (
        item_id INT AUTO_INCREMENT PRIMARY KEY,
        purchase_order_id INT NOT NULL,
        product_id INT NOT NULL,
        quantity_ordered INT NOT NULL,
        quantity_received INT NOT NULL DEFAULT 0,
        unit_cost DECIMAL(10,2) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_poi_order
            FOREIGN KEY (purchase_order_id)
            REFERENCES purchase_orders(purchase_order_id),
        CONSTRAINT fk_poi_product
            FOREIGN KEY (product_id)
            REFERENCES products(product_id),
        INDEX idx_poi_product (product_id)
    ) ENGINE=InnoDB
    """
]


def initialize_inventory_modules():
    with engine.begin() as connection:
        for statement in TABLES:
            connection.execute(text(statement))

    print("Database migration completed successfully.")
    print("Suppliers table: READY")
    print("Purchase orders table: READY")
    print("Purchase order items table: READY")
    print("Existing products and inventory tables were not modified.")


if __name__ == "__main__":
    initialize_inventory_modules()
