from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
base = pd.read_csv(
    BASE_DIR / "kkbox_leakage_safe_model_dataset.csv",
    usecols=["msno", "is_churn"],
)
recent = pd.read_csv(BASE_DIR / "model_dataset_recent_usage.csv")
df = base.merge(recent, on="msno", how="left", validate="one_to_one")
print(f"Customers: {len(df):,}   Missing recent-usage rows: "
      f"{int(df['active_days_last_30'].isna().sum())}")


def churn_by(frame, col):
    out = frame.groupby(col, observed=True)["is_churn"].agg(
        customers="count", churned="sum", churn_rate="mean"
    )
    out["churn_rate"] = (out["churn_rate"] * 100).round(2)
    return out


print("\nAVERAGES, RETAINED (0) vs CHURNED (1)")
cols = ["active_days_last_7", "active_days_last_30",
        "listening_secs_last_30", "active_days_change_30"]
print(df.groupby("is_churn")[cols].mean().round(2).to_string())

print("\nCHURN BY ACTIVE DAYS IN LAST 30")
df["band_30"] = pd.cut(
    df["active_days_last_30"],
    bins=[-1, 0, 7, 14, 21, 30],
    labels=["0 days", "1-7", "8-14", "15-21", "22-30"],
)
print(churn_by(df, "band_30").to_string())

print("\nCHURN BY CHANGE VS PRIOR 30 DAYS")
df["change_band"] = pd.cut(
    df["active_days_change_30"],
    bins=[-31, -8, -1, 0, 7, 31],
    labels=["fell 8+", "fell 1-7", "no change", "rose 1-7", "rose 8+"],
)
print(churn_by(df, "change_band").to_string())

print("\nCHURN BY ANY LISTENING IN LAST 7 DAYS")
df["any_last_7"] = np.where(df["active_days_last_7"] > 0, "yes", "no")
print(churn_by(df, "any_last_7").to_string())