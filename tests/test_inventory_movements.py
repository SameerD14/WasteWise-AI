from datetime import date

import pytest

from app.components.inventory_view import calculate_stock_movement


def test_sold_movement_reduces_stock():
    assert calculate_stock_movement(
        10, "Sold", 3, "Customer sale",
        today=date(2026, 11, 12)
    ) == 7


def test_expired_batch_cannot_be_sold():
    with pytest.raises(ValueError, match="expired"):
        calculate_stock_movement(
            10, "Sold", 1, "Sale",
            expiry_date=date(2026, 11, 10),
            today=date(2026, 11, 12)
        )


def test_expired_batch_cannot_be_consumed():
    with pytest.raises(ValueError, match="expired"):
        calculate_stock_movement(
            10, "Consumed", 1, "Kitchen use",
            expiry_date=date(2026, 11, 10),
            today=date(2026, 11, 12)
        )


def test_expired_stock_can_be_written_off_as_waste():
    assert calculate_stock_movement(
        5, "Wasted", 2, "Expired stock disposal",
        expiry_date=date(2026, 11, 10),
        today=date(2026, 11, 12)
    ) == 3


def test_insufficient_stock_is_rejected():
    with pytest.raises(ValueError, match="available"):
        calculate_stock_movement(2, "Sold", 3, "Sale")


def test_blank_reason_is_rejected():
    with pytest.raises(ValueError, match="reason"):
        calculate_stock_movement(5, "Sold", 1, "  ")


def test_adjustment_increase():
    assert calculate_stock_movement(
        5, "Adjustment", 4, "Stock correction",
        adjustment_direction="Increase"
    ) == 9


def test_adjustment_decrease():
    assert calculate_stock_movement(
        5, "Adjustment", 2, "Stock correction",
        adjustment_direction="Decrease"
    ) == 3


def test_zero_quantity_is_rejected():
    with pytest.raises(ValueError, match="greater than zero"):
        calculate_stock_movement(5, "Sold", 0, "Sale")


def test_same_day_expiry_is_not_treated_as_expired():
    assert calculate_stock_movement(
        5, "Sold", 1, "Sale",
        expiry_date=date(2026, 11, 12),
        today=date(2026, 11, 12)
    ) == 4
