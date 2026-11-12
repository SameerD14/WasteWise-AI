import pandas as pd


def generate_inventory_recommendations(
    inventory_df: pd.DataFrame,
    predictions_df: pd.DataFrame
) -> pd.DataFrame:

    df = inventory_df.merge(
        predictions_df,
        on="batch_id",
        how="left",
        validate="one_to_one"
    )

    recommendations = []

    for _, row in df.iterrows():

        status = row["risk_status"]

        if pd.isna(status):
            status = "Data Incomplete"

        days = pd.to_numeric(
            pd.Series([row["days_to_expiry"]]),
            errors="coerce"
        ).iloc[0]

        surplus = pd.to_numeric(
            pd.Series([row["inventory_surplus"]]),
            errors="coerce"
        ).iloc[0]

        if pd.isna(surplus):
            surplus = 0

        if status == "Expired":
            priority = "Critical"
            action = (
                "Do not sell. Follow food-safety "
                "disposal policy."
            )

        elif status == "Expires Today - Immediate Review":
            priority = "Critical"
            action = (
                "Arrange immediate manager and "
                "food-safety review."
            )

        elif status == "Data Incomplete":
            priority = "Review"
            action = (
                "Complete and verify missing inventory data "
                "before relying on the risk prediction."
            )

        elif status == "High Risk" and surplus > 0:
            priority = "High"
            action = (
                "Review excess stock and expected demand. "
                "Assess safe stock-reduction options."
            )

        elif status == "High Risk":
            priority = "High"
            action = (
                "Investigate demand and expiry information. "
                "Monitor this batch closely."
            )

        elif surplus > 0 and pd.notna(days) and days <= 3:
            priority = "High"
            action = (
                "Review excess stock and near expiry. "
                "Check safe inventory options."
            )

        elif surplus > 0:
            priority = "Review"
            action = (
                "Review excess stock against expected demand."
            )

        else:
            priority = "Normal"
            action = "Continue regular inventory monitoring."

        recommendations.append({
            "batch_id": row["batch_id"],
            "product_name": row["product_name"],
            "days_to_expiry": days,
            "quantity_remaining": row["quantity_remaining"],
            "inventory_surplus": row["inventory_surplus"],
            "risk_status": status,
            "risk_probability": row["risk_probability"],
            "priority": priority,
            "recommended_action": action
        })

    return pd.DataFrame(recommendations)
