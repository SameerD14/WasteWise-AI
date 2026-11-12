import pandas as pd

from src.recommendations.recommendation_engine import (
    generate_inventory_recommendations
)


def make_recommendation_data(status, days, surplus):
    inventory = pd.DataFrame([{
        "batch_id": 1001,
        "product_name": "Milk 500ml",
        "days_to_expiry": days,
        "quantity_remaining": 50,
        "inventory_surplus": surplus
    }])

    predictions = pd.DataFrame([{
        "batch_id": 1001,
        "risk_status": status,
        "risk_probability": 95.0
    }])

    return generate_inventory_recommendations(inventory, predictions)


def test_expired_batch_gets_critical_priority():
    result = make_recommendation_data("Expired", -2, 10)

    assert result.loc[0, "priority"] == "Critical"
    assert "Do not sell" in result.loc[0, "recommended_action"]


def test_expires_today_gets_critical_priority():
    result = make_recommendation_data(
        "Expires Today - Immediate Review", 0, 10
    )

    assert result.loc[0, "priority"] == "Critical"
    assert "immediate" in result.loc[0, "recommended_action"].lower()


def test_data_incomplete_gets_review_priority():
    result = make_recommendation_data("Data Incomplete", 5, 0)

    assert result.loc[0, "priority"] == "Review"


def test_high_risk_with_surplus_gets_high_priority():
    result = make_recommendation_data("High Risk", 5, 20)

    assert result.loc[0, "priority"] == "High"
    assert "excess stock" in result.loc[0, "recommended_action"].lower()


def test_low_risk_near_expiry_with_surplus_gets_high_priority():
    result = make_recommendation_data("Low Risk", 2, 10)

    assert result.loc[0, "priority"] == "High"


def test_low_risk_with_surplus_gets_review_priority():
    result = make_recommendation_data("Low Risk", 7, 10)

    assert result.loc[0, "priority"] == "Review"


def test_low_risk_without_surplus_gets_normal_priority():
    result = make_recommendation_data("Low Risk", 7, 0)

    assert result.loc[0, "priority"] == "Normal"
