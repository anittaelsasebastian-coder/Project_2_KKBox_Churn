import os
import pandas as pd
import numpy as np


# ============================================================
# PROJECT 2 — KKBOX CHURN
# STEP 5 — VALIDATE LEAKAGE-SAFE MODEL DATASET
# ============================================================

print("=" * 78)
print("PROJECT 2 — KKBOX CHURN")
print("STEP 5 — VALIDATE LEAKAGE-SAFE MODEL DATASET")
print("=" * 78)


# ------------------------------------------------------------
# 1. SETTINGS
# ------------------------------------------------------------

MODEL_FILE = "kkbox_leakage_safe_model_dataset.csv"

CUTOFF_DATE = pd.Timestamp("2017-02-28")


# ------------------------------------------------------------
# 2. CHECK FILE
# ------------------------------------------------------------

print("\n1. CHECKING MODEL DATASET")
print("-" * 78)

if not os.path.exists(MODEL_FILE):
    raise FileNotFoundError(
        f"Could not find {MODEL_FILE}"
    )

print(f"{MODEL_FILE:<55} OK")


# ------------------------------------------------------------
# 3. LOAD DATASET
# ------------------------------------------------------------

print("\n2. LOADING DATASET")
print("-" * 78)

df = pd.read_csv(MODEL_FILE)

print(f"Rows: {len(df):,}")
print(f"Columns: {len(df.columns):,}")


# ------------------------------------------------------------
# 4. CUSTOMER / ROW INTEGRITY
# ------------------------------------------------------------

print("\n3. CUSTOMER / ROW INTEGRITY")
print("-" * 78)

row_count = len(df)
unique_customers = df["msno"].nunique()
duplicate_rows = df.duplicated().sum()
duplicate_customers = df["msno"].duplicated().sum()

print(f"Rows: {row_count:,}")
print(f"Unique customers: {unique_customers:,}")
print(f"Duplicate rows: {duplicate_rows:,}")
print(f"Duplicate customer IDs: {duplicate_customers:,}")


if row_count != 7500:
    raise ValueError(
        f"Expected 7,500 rows, found {row_count:,}."
    )

if unique_customers != 7500:
    raise ValueError(
        f"Expected 7,500 unique customers, found {unique_customers:,}."
    )

if duplicate_rows != 0:
    raise ValueError(
        "Duplicate rows detected."
    )

if duplicate_customers != 0:
    raise ValueError(
        "Duplicate customer IDs detected."
    )

print("ROW/CUSTOMER INTEGRITY: PASS")


# ------------------------------------------------------------
# 5. TARGET VALIDATION
# ------------------------------------------------------------

print("\n4. TARGET VALIDATION")
print("-" * 78)

target_counts = df["is_churn"].value_counts(dropna=False)

churned = (df["is_churn"] == 1).sum()
retained = (df["is_churn"] == 0).sum()
missing_target = df["is_churn"].isna().sum()

churn_rate = churned / len(df)

print(f"Churned: {churned:,}")
print(f"Retained: {retained:,}")
print(f"Missing target: {missing_target:,}")
print(f"Churn rate: {churn_rate:.2%}")


if churned != 711:
    raise ValueError(
        f"Expected 711 churned customers, found {churned:,}."
    )

if retained != 6789:
    raise ValueError(
        f"Expected 6,789 retained customers, found {retained:,}."
    )

if missing_target != 0:
    raise ValueError(
        "Missing churn targets detected."
    )

if not set(df["is_churn"].unique()).issubset({0, 1}):
    raise ValueError(
        "Unexpected values found in is_churn."
    )

print("TARGET VALIDATION: PASS")


# ------------------------------------------------------------
# 6. MISSING VALUES
# ------------------------------------------------------------

print("\n5. MISSING VALUE CHECK")
print("-" * 78)

missing = (
    df.isna()
    .sum()
    .sort_values(ascending=False)
)

missing_pct = (
    missing / len(df) * 100
)

missing_table = pd.DataFrame({
    "missing_count": missing,
    "missing_percent": missing_pct.round(2)
})

print(missing_table.to_string())


missing_table.to_csv(
    "model_dataset_missing_values.csv"
)

print("\nSaved: model_dataset_missing_values.csv")


# ------------------------------------------------------------
# 7. DATA TYPES
# ------------------------------------------------------------

print("\n6. DATA TYPE CHECK")
print("-" * 78)

dtype_table = pd.DataFrame({
    "column": df.columns,
    "dtype": df.dtypes.astype(str).values
})

print(dtype_table.to_string(index=False))

dtype_table.to_csv(
    "model_dataset_dtypes.csv",
    index=False
)

print("\nSaved: model_dataset_dtypes.csv")


# ------------------------------------------------------------
# 8. FEATURE LIST
# ------------------------------------------------------------

print("\n7. FEATURE LIST")
print("-" * 78)

for i, column in enumerate(df.columns, start=1):
    print(f"{i:02d}. {column}")


# ------------------------------------------------------------
# 9. DATE CONVERSION FOR VALIDATION
# ------------------------------------------------------------

date_columns = [
    "registration_init_time",
    "first_transaction_date",
    "latest_transaction_date",
    "latest_membership_expire_date",
    "first_active_date",
    "last_active_date",
]

for column in date_columns:

    if column in df.columns:

        df[column] = pd.to_datetime(
            df[column],
            errors="coerce"
        )


# ------------------------------------------------------------
# 10. DATE / LEAKAGE VALIDATION
# ------------------------------------------------------------

print("\n8. DATE AND LEAKAGE CHECK")
print("-" * 78)

leakage_columns = [
    "latest_transaction_date",
    "latest_membership_expire_date",
    "first_transaction_date",
    "first_active_date",
    "last_active_date",
]

for column in leakage_columns:

    if column in df.columns:

        invalid = (
            df[column] > CUTOFF_DATE
        ).sum()

        print(
            f"{column:<35} after cutoff: {invalid:,}"
        )

        if invalid != 0:
            raise ValueError(
                f"Potential leakage detected in {column}."
            )

print("DATE/LEAKAGE CHECK: PASS")


# ------------------------------------------------------------
# 11. NEGATIVE / IMPOSSIBLE VALUES
# ------------------------------------------------------------

print("\n9. NUMERIC LOGIC CHECK")
print("-" * 78)

numeric_columns = df.select_dtypes(
    include=np.number
).columns.tolist()

numeric_summary = df[numeric_columns].describe().T

print(
    numeric_summary[
        ["count", "mean", "std", "min", "max"]
    ].to_string()
)

numeric_summary.to_csv(
    "model_dataset_numeric_summary.csv"
)

print("\nSaved: model_dataset_numeric_summary.csv")


# ------------------------------------------------------------
# 12. SPECIFIC LOGIC CHECKS
# ------------------------------------------------------------

print("\n10. BUSINESS LOGIC CHECKS")
print("-" * 78)


# Recency should never be negative
recency_columns = [
    "days_since_latest_transaction",
    "days_since_last_activity",
]

for column in recency_columns:

    if column in df.columns:

        negative_count = (
            df[column].dropna() < 0
        ).sum()

        print(
            f"{column:<35} negative values: "
            f"{negative_count:,}"
        )

        if negative_count != 0:
            raise ValueError(
                f"Negative values found in {column}."
            )


# Counts should not be negative
count_columns = [
    "transaction_count",
    "cancellation_count",
    "active_days",
    "total_unique_songs",
]

for column in count_columns:

    if column in df.columns:

        negative_count = (
            df[column].dropna() < 0
        ).sum()

        print(
            f"{column:<35} negative values: "
            f"{negative_count:,}"
        )

        if negative_count != 0:
            raise ValueError(
                f"Negative values found in {column}."
            )


print("BUSINESS LOGIC CHECKS: PASS")


# ------------------------------------------------------------
# 13. HISTORY FLAGS
# ------------------------------------------------------------

print("\n11. HISTORY FLAG CHECK")
print("-" * 78)

if "has_transaction_history" in df.columns:

    expected_transaction_flag = (
        df["transaction_count"].fillna(0) > 0
    ).astype(int)

    mismatches = (
        df["has_transaction_history"]
        != expected_transaction_flag
    ).sum()

    print(
        f"Transaction history flag mismatches: "
        f"{mismatches:,}"
    )

    if mismatches != 0:
        raise ValueError(
            "Transaction history flag is inconsistent."
        )


if "has_usage_history" in df.columns:

    expected_usage_flag = (
        df["active_days"].fillna(0) > 0
    ).astype(int)

    mismatches = (
        df["has_usage_history"]
        != expected_usage_flag
    ).sum()

    print(
        f"Usage history flag mismatches: "
        f"{mismatches:,}"
    )

    if mismatches != 0:
        raise ValueError(
            "Usage history flag is inconsistent."
        )


print("HISTORY FLAGS: PASS")


# ------------------------------------------------------------
# 14. CHURN BY HISTORY AVAILABILITY
# ------------------------------------------------------------

print("\n12. CHURN BY DATA AVAILABILITY")
print("-" * 78)

if "has_transaction_history" in df.columns:

    transaction_history_summary = (
        df.groupby("has_transaction_history")
        .agg(
            customers=("msno", "count"),
            churned=("is_churn", "sum"),
            churn_rate=("is_churn", "mean")
        )
        .reset_index()
    )

    transaction_history_summary["churn_rate"] *= 100

    print("\nTransaction history:")
    print(
        transaction_history_summary.to_string(
            index=False
        )
    )

if "has_usage_history" in df.columns:

    usage_history_summary = (
        df.groupby("has_usage_history")
        .agg(
            customers=("msno", "count"),
            churned=("is_churn", "sum"),
            churn_rate=("is_churn", "mean")
        )
        .reset_index()
    )

    usage_history_summary["churn_rate"] *= 100

    print("\nUsage history:")
    print(
        usage_history_summary.to_string(
            index=False
        )
    )


# ------------------------------------------------------------
# 15. FEATURE MISSINGNESS BY CHURN
# ------------------------------------------------------------

print("\n13. MISSINGNESS BY CHURN")
print("-" * 78)

missing_by_churn = []

for column in df.columns:

    if column in ["msno", "is_churn"]:
        continue

    for churn_value in [0, 1]:

        subset = df[
            df["is_churn"] == churn_value
        ]

        missing_count = subset[column].isna().sum()

        missing_percent = (
            missing_count / len(subset) * 100
        )

        missing_by_churn.append({
            "feature": column,
            "is_churn": churn_value,
            "missing_count": missing_count,
            "missing_percent": missing_percent,
        })


missing_by_churn_df = pd.DataFrame(
    missing_by_churn
)

missing_by_churn_df.to_csv(
    "model_dataset_missingness_by_churn.csv",
    index=False
)

print(
    "Saved: model_dataset_missingness_by_churn.csv"
)


# ------------------------------------------------------------
# 16. HIGH-CARDINALITY / CATEGORICAL CHECK
# ------------------------------------------------------------

print("\n14. CATEGORICAL FEATURE CHECK")
print("-" * 78)

categorical_columns = df.select_dtypes(
    include=["object"]
).columns.tolist()

for column in categorical_columns:

    unique_count = df[column].nunique(
        dropna=True
    )

    print(
        f"{column:<35} unique values: "
        f"{unique_count:,}"
    )


# ------------------------------------------------------------
# 17. FINAL VALIDATION STATUS
# ------------------------------------------------------------

print("\n" + "=" * 78)
print("STEP 5 VALIDATION STATUS")
print("=" * 78)

print("Row integrity: PASS")
print("Customer uniqueness: PASS")
print("Target integrity: PASS")
print("Missing-value report: CREATED")
print("Data-type report: CREATED")
print("Numeric summary: CREATED")
print("Date/leakage check: PASS")
print("Negative-value checks: PASS")
print("History flags: PASS")
print("Missingness-by-churn report: CREATED")

print("\nNext step:")
print("Review validation results before statistical modeling.")