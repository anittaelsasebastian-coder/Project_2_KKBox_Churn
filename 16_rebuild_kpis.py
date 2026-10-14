from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
df = pd.read_csv(BASE_DIR / "kkbox_leakage_safe_model_dataset.csv")


def churn_table(frame, group_col):
    out = frame.groupby(group_col, dropna=False)["is_churn"].agg(
        customers="count", churned="sum", churn_rate="mean"
    )
    out["churn_rate"] = (out["churn_rate"] * 100).round(2)
    return out


print("OVERALL")
print(f"Customers: {len(df):,}")
print(f"Churned: {int(df['is_churn'].sum()):,}")
print(f"Churn rate: {df['is_churn'].mean() * 100:.2f}%")

print("\nCHURN BY LATEST RENEWAL TYPE (1 = auto-renew, 0 = manual)")
df["renewal_type"] = df["latest_is_auto_renew"].map(
    {1: "auto-renew", 0: "manual-renew"}
).fillna("no transaction history")
print(churn_table(df, "renewal_type").to_string())

print("\nCHURN BY DAYS SINCE LATEST TRANSACTION")
df["recency_group"] = pd.cut(
    df["days_since_latest_transaction"],
    bins=[-1, 7, 30, np.inf],
    labels=["0-7 days", "8-30 days", "31+ days"],
).astype(object)
df.loc[df["has_transaction_history"] == 0, "recency_group"] = "no history"
print(churn_table(df, "recency_group").to_string())

print("\nCHURN BY USAGE HISTORY (1 = has pre-cutoff listening)")
print(churn_table(df, "has_usage_history").to_string())

print("\nAVERAGE USAGE, CHURNED (1) vs RETAINED (0)")
usage_cols = ["active_days", "total_unique_songs", "total_listening_secs"]
print(df.groupby("is_churn")[usage_cols].mean().round(2).to_string())

print("\nMONTHLY-EQUIVALENT REVENUE (latest paid amount / plan days x 30)")
valid = df["latest_payment_plan_days"] > 0
df["monthly_revenue"] = np.where(
    valid,
    df["latest_actual_amount_paid"] / df["latest_payment_plan_days"] * 30,
    np.nan,
)
print(f"Customers with a usable revenue value: {int(df['monthly_revenue'].notna().sum()):,}")
print(df.groupby("is_churn")["monthly_revenue"].agg(
    ["count", "mean", "median"]).round(2).to_string())

print("\nILLUSTRATIVE SCENARIO (not a forecast)")
manual = df[df["renewal_type"] == "manual-renew"]
avoided = len(manual) * 0.05
churned_manual_rev = manual.loc[manual["is_churn"] == 1, "monthly_revenue"].mean()
print(f"Manual-renew customers: {len(manual):,}")
print(f"Churners avoided if churn fell 5 percentage points: {avoided:.2f}")
print(f"Average monthly revenue of churned manual-renew customers: {churned_manual_rev:.2f}")
print(f"Monthly revenue preserved: {avoided * churned_manual_rev:,.2f}")
print(f"Annualized: {avoided * churned_manual_rev * 12:,.2f}")