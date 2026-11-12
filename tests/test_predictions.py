import pandas as pd
import pytest

from src.models.predict import predict_inventory_risk, model_features


def make_valid_batch(batch_id=1001):
    values = {
        "batch_id": batch_id,
        "quantity_remaining": 50,
        "initial_quantity": 100,
        "days_to_expiry": 5,
        "avg_daily_sales_7d": 10,
        "expected_demand_before_expiry": 40,
        "unit_price": 100,
        "unit_cost": 60,
        "discount_pct": 0.10,
        "stock_coverage_days": 5,
        "remaining_stock_pct": 50,
        "profit_per_unit": 40,
        "gross_margin_pct": 40,
    }

    return values


def test_expired_batch_is_blocked():
    batch = make_valid_batch()
    batch["days_to_expiry"] = -2

    result = predict_inventory_risk(pd.DataFrame([batch]))

    assert result.loc[0, "risk_status"] == "Expired"
    assert pd.isna(result.loc[0, "risk_probability"])
    assert "Do not sell" in result.loc[0, "action"]


def test_batch_expiring_today_needs_review():
    batch = make_valid_batch()
    batch["days_to_expiry"] = 0

    result = predict_inventory_risk(pd.DataFrame([batch]))

    assert result.loc[0, "risk_status"] == "Expires Today - Immediate Review"
    assert pd.isna(result.loc[0, "risk_probability"])


def test_missing_expiry_information():
    batch = make_valid_batch()
    batch["days_to_expiry"] = None

    result = predict_inventory_risk(pd.DataFrame([batch]))

    assert result.loc[0, "risk_status"] == "Data Incomplete"


def test_missing_model_feature_raises_error():
    batch = make_valid_batch()
    batch.pop(model_features[0])

    with pytest.raises(ValueError, match="Missing required model features"):
        predict_inventory_risk(pd.DataFrame([batch]))


def test_valid_batch_returns_prediction():
    batch = make_valid_batch()

    result = predict_inventory_risk(pd.DataFrame([batch]))

    assert result.loc[0, "risk_status"] in ["High Risk", "Low Risk"]
    assert 0 <= result.loc[0, "risk_probability"] <= 100
    assert result.loc[0, "batch_id"] == 1001
