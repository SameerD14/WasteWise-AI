
import pandas as pd

from sqlalchemy import text
from src.database.connection import engine


DASHBOARD_QUERY = """
SELECT
    i.batch_id,
    p.product_id,
    p.product_name,
    i.category,
    i.snapshot_date,
    i.expiry_date,
    i.initial_quantity,
    i.quantity_remaining,
    i.days_to_expiry,
    i.avg_daily_sales_7d,
    i.expected_demand_before_expiry,
    i.inventory_surplus,
    i.stock_coverage_days,
    i.unit_price,
    i.unit_cost,
    i.discount_pct,
    pr.risk_status,
    pr.risk_probability,
    r.priority,
    r.recommended_action
FROM inventory_batches AS i
INNER JOIN products AS p
    ON i.product_id = p.product_id
INNER JOIN predictions AS pr
    ON i.batch_id = pr.batch_id
INNER JOIN recommendations AS r
    ON i.batch_id = r.batch_id
ORDER BY i.batch_id
"""


def load_inventory_data():

    with engine.connect() as connection:

        df = pd.read_sql(
            text(DASHBOARD_QUERY),
            connection
        )

    if df.empty:
        raise ValueError("No inventory records found.")

    return df


def load_products():

    query = """
    SELECT
        product_id,
        product_name,
        category,
        shelf_life_days,
        selling_price,
        unit_cost
    FROM products
    ORDER BY product_name
    """

    with engine.connect() as connection:
        return pd.read_sql(text(query), connection)
