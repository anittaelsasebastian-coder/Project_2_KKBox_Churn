import os
import pandas as pd


# ============================================================
# PROJECT 2 — KKBOX CHURN
# STEP 4 — BUILD LEAKAGE-SAFE MODEL DATASET
# ============================================================

print("=" * 78)
print("PROJECT 2 — KKBOX CHURN")
print("STEP 4 — BUILD LEAKAGE-SAFE MODEL DATASET")
print("=" * 78)


# ------------------------------------------------------------
# 1. SETTINGS
# ------------------------------------------------------------

RAW_DIR = "raw_data"

SAMPLE_FILE = "Project_2_KKBox_Churn_Analysis.csv"
MEMBERS_FILE = os.path.join(RAW_DIR, "members_v3.csv")
TRAIN_FILE = os.path.join(RAW_DIR, "train_v2.csv")
TRANSACTIONS_FILE = os.path.join(RAW_DIR, "transactions.csv")
USER_LOGS_FILE = os.path.join(RAW_DIR, "user_logs.csv")

OUTPUT_FILE = "kkbox_leakage_safe_model_dataset.csv"

CUTOFF_DATE = pd.Timestamp("2017-02-28")
CHUNK_SIZE = 250_000


# ------------------------------------------------------------
# 2. CHECK FILES
# ------------------------------------------------------------

print("\n1. CHECKING REQUIRED FILES")
print("-" * 78)

for file in [
    SAMPLE_FILE,
    MEMBERS_FILE,
    TRAIN_FILE,
    TRANSACTIONS_FILE,
    USER_LOGS_FILE,
]:
    if not os.path.exists(file):
        raise FileNotFoundError(f"Missing file: {file}")
    print(f"{file:<55} OK")


# ------------------------------------------------------------
# 3. LOAD THE EXISTING 7,500-CUSTOMER SAMPLE
# ------------------------------------------------------------

print("\n2. LOADING EXISTING 7,500-CUSTOMER SAMPLE")
print("-" * 78)

sample = pd.read_csv(
    SAMPLE_FILE,
    usecols=["msno", "is_churn"]
)

sample["msno"] = (
    sample["msno"]
    .astype(str)
    .str.lstrip("'")
)

print(f"Sample customers: {len(sample):,}")
print(f"Unique customers: {sample['msno'].nunique():,}")
print(f"Churned: {(sample['is_churn'] == 1).sum():,}")
print(f"Retained: {(sample['is_churn'] == 0).sum():,}")


if len(sample) != 7500:
    raise ValueError(
        f"Expected exactly 7,500 sample customers, found {len(sample):,}."
    )

if sample["msno"].nunique() != 7500:
    raise ValueError(
        "The sample does not contain 7,500 unique customers."
    )


sample_ids = set(sample["msno"])


# ------------------------------------------------------------
# 4. VERIFY TARGET AGAINST TRAIN_V2
# ------------------------------------------------------------

print("\n3. VERIFYING TARGET AGAINST TRAIN_V2")
print("-" * 78)

train = pd.read_csv(
    TRAIN_FILE,
    usecols=["msno", "is_churn"]
)

train["msno"] = (
    train["msno"]
    .astype(str)
    .str.lstrip("'")
)

train_sample = train[
    train["msno"].isin(sample_ids)
].copy()

print(f"Matching train_v2 customers: {len(train_sample):,}")
print(f"Unique matching customers: {train_sample['msno'].nunique():,}")


if len(train_sample) != 7500:
    raise ValueError(
        f"Expected 7,500 train_v2 matches, found {len(train_sample):,}."
    )


target_check = sample.merge(
    train_sample,
    on="msno",
    how="left",
    suffixes=("_sample", "_train"),
    validate="one_to_one"
)

target_mismatches = (
    target_check["is_churn_sample"]
    != target_check["is_churn_train"]
).sum()

print(f"Target mismatches: {target_mismatches:,}")


if target_mismatches != 0:
    raise ValueError(
        "Target mismatch detected between sample and train_v2."
    )

print("TARGET RECONCILIATION: PASS")


# Keep the verified target
target = target_check[
    ["msno", "is_churn_sample"]
].rename(
    columns={"is_churn_sample": "is_churn"}
)


# ------------------------------------------------------------
# 5. MEMBER FEATURES
# ------------------------------------------------------------

print("\n4. BUILDING MEMBER FEATURES")
print("-" * 78)

members = pd.read_csv(
    MEMBERS_FILE,
    usecols=[
        "msno",
        "city",
        "bd",
        "gender",
        "registered_via",
        "registration_init_time",
    ]
)

members["msno"] = (
    members["msno"]
    .astype(str)
    .str.lstrip("'")
)

members = members[
    members["msno"].isin(sample_ids)
].copy()

print(f"Matching member records: {len(members):,}")


if len(members) != 7500:
    raise ValueError(
        f"Expected 7,500 member records, found {len(members):,}."
    )


if members["msno"].nunique() != 7500:
    raise ValueError(
        "Duplicate member records found."
    )


members["registration_init_time"] = pd.to_datetime(
    members["registration_init_time"].astype(str),
    format="%Y%m%d",
    errors="coerce"
)

# Registration must be on or before the prediction cutoff.
members.loc[
    members["registration_init_time"] > CUTOFF_DATE,
    "registration_init_time"
] = pd.NaT

members["registration_days_before_cutoff"] = (
    CUTOFF_DATE -
    members["registration_init_time"]
).dt.days


# ------------------------------------------------------------
# AGE GROUP
# ------------------------------------------------------------

members["age_group"] = "Unknown"

valid_age = members["bd"].between(
    13,
    100,
    inclusive="both"
)

members.loc[
    valid_age & members["bd"].between(13, 17),
    "age_group"
] = "13-17"

members.loc[
    valid_age & members["bd"].between(18, 24),
    "age_group"
] = "18-24"

members.loc[
    valid_age & members["bd"].between(25, 34),
    "age_group"
] = "25-34"

members.loc[
    valid_age & members["bd"].between(35, 44),
    "age_group"
] = "35-44"

members.loc[
    valid_age & members["bd"].between(45, 54),
    "age_group"
] = "45-54"

members.loc[
    valid_age & members["bd"].between(55, 100),
    "age_group"
] = "55+"


# Raw bd is deliberately NOT included.
members = members.drop(columns=["bd"])


# ------------------------------------------------------------
# 6. TRANSACTION FEATURES
# ------------------------------------------------------------

print("\n5. SCANNING TRANSACTIONS")
print("-" * 78)

transaction_columns = [
    "msno",
    "payment_method_id",
    "payment_plan_days",
    "plan_list_price",
    "actual_amount_paid",
    "is_auto_renew",
    "transaction_date",
    "membership_expire_date",
    "is_cancel",
]

transaction_parts = []
transaction_rows = 0

for chunk in pd.read_csv(
    TRANSACTIONS_FILE,
    usecols=transaction_columns,
    chunksize=CHUNK_SIZE
):

    chunk["msno"] = (
        chunk["msno"]
        .astype(str)
        .str.lstrip("'")
    )

    chunk["transaction_date"] = pd.to_datetime(
        chunk["transaction_date"].astype(str),
        format="%Y%m%d",
        errors="coerce"
    )

    chunk = chunk[
        (chunk["msno"].isin(sample_ids)) &
        (chunk["transaction_date"] <= CUTOFF_DATE)
    ].copy()

    if not chunk.empty:
        transaction_parts.append(chunk)
        transaction_rows += len(chunk)


print(
    f"Matching pre-cutoff transaction rows: "
    f"{transaction_rows:,}"
)


if transaction_parts:

    transactions = pd.concat(
        transaction_parts,
        ignore_index=True
    )

else:

    transactions = pd.DataFrame(
        columns=transaction_columns
    )


# ------------------------------------------------------------
# TRANSACTION AGGREGATES
# ------------------------------------------------------------

if not transactions.empty:

    transactions = transactions.sort_values(
        ["msno", "transaction_date"]
    )

    transaction_features = (
        transactions
        .groupby("msno")
        .agg(
            transaction_count=("transaction_date", "count"),
            cancellation_count=("is_cancel", "sum"),
            first_transaction_date=("transaction_date", "min"),
            latest_transaction_date=("transaction_date", "max"),
            total_actual_amount_paid=("actual_amount_paid", "sum"),
            average_actual_amount_paid=("actual_amount_paid", "mean"),
            total_plan_list_price=("plan_list_price", "sum"),
            average_plan_list_price=("plan_list_price", "mean"),
        )
        .reset_index()
    )

    latest = (
        transactions
        .sort_values(
            ["msno", "transaction_date"]
        )
        .groupby("msno")
        .tail(1)
        [
            [
                "msno",
                "payment_method_id",
                "payment_plan_days",
                "plan_list_price",
                "actual_amount_paid",
                "is_auto_renew",
                "is_cancel",
                "membership_expire_date",
            ]
        ]
        .copy()
    )

    latest = latest.rename(
        columns={
            "payment_method_id": "latest_payment_method_id",
            "payment_plan_days": "latest_payment_plan_days",
            "plan_list_price": "latest_plan_list_price",
            "actual_amount_paid": "latest_actual_amount_paid",
            "is_auto_renew": "latest_is_auto_renew",
            "is_cancel": "latest_is_cancel",
            "membership_expire_date": "latest_membership_expire_date",
        }
    )

    transaction_features = transaction_features.merge(
        latest,
        on="msno",
        how="left",
        validate="one_to_one"
    )

    transaction_features[
    "days_since_latest_transaction"
    ] = (
    CUTOFF_DATE -
    pd.to_datetime(
        transaction_features["latest_transaction_date"],
        errors="coerce"
    )
    ).dt.days

else:

    transaction_features = pd.DataFrame(
        {"msno": list(sample_ids)}
    )


# ------------------------------------------------------------
# 7. USER LOG FEATURES
# ------------------------------------------------------------

print("\n6. SCANNING USER LOGS")
print("-" * 78)

usage_columns = [
    "msno",
    "date",
    "num_25",
    "num_50",
    "num_75",
    "num_985",
    "num_100",
    "num_unq",
    "total_secs",
]

usage_parts = []
usage_rows = 0

for chunk in pd.read_csv(
    USER_LOGS_FILE,
    usecols=usage_columns,
    chunksize=CHUNK_SIZE
):

    chunk["msno"] = (
        chunk["msno"]
        .astype(str)
        .str.lstrip("'")
    )

    chunk["date"] = pd.to_datetime(
        chunk["date"].astype(str),
        format="%Y%m%d",
        errors="coerce"
    )
    chunk["total_secs"] = pd.to_numeric(
        chunk["total_secs"],
        errors="coerce"
)

    chunk["num_unq"] = pd.to_numeric(
        chunk["num_unq"],
        errors="coerce"
)

    chunk = chunk[
        (chunk["msno"].isin(sample_ids)) &
        (chunk["date"] <= CUTOFF_DATE)
    ].copy()
    chunk = chunk[
        chunk["total_secs"].notna() &
        (chunk["total_secs"] >= 0)
    ].copy()

    if not chunk.empty:
        usage_parts.append(chunk)
        usage_rows += len(chunk)


print(
    f"Matching pre-cutoff usage rows: "
    f"{usage_rows:,}"
)


if usage_parts:

    usage = pd.concat(
        usage_parts,
        ignore_index=True
    )

else:

    usage = pd.DataFrame(
        columns=usage_columns
    )


# ------------------------------------------------------------
# USAGE AGGREGATES
# ------------------------------------------------------------

if not usage.empty:

    usage_features = (
        usage
        .groupby("msno")
        .agg(
            active_days=("date", "nunique"),
            total_unique_songs=("num_unq", "sum"),
            total_listening_secs=("total_secs", "sum"),
            average_daily_listening_secs=("total_secs", "mean"),
            first_active_date=("date", "min"),
            last_active_date=("date", "max"),
        )
        .reset_index()
    )

    usage_features[
        "days_since_last_activity"
    ] = (
        CUTOFF_DATE -
        pd.to_datetime(
            usage_features["last_active_date"],
            errors="coerce"
        )
    ).dt.days

else:

    usage_features = pd.DataFrame(
        {"msno": list(sample_ids)}
    )


# ------------------------------------------------------------
# 8. MERGE ALL FEATURES
# ------------------------------------------------------------

print("\n7. MERGING MODEL DATASET")
print("-" * 78)

model = target.copy()

model = model.merge(
    members,
    on="msno",
    how="left",
    validate="one_to_one"
)

model = model.merge(
    transaction_features,
    on="msno",
    how="left",
    validate="one_to_one"
)

model = model.merge(
    usage_features,
    on="msno",
    how="left",
    validate="one_to_one"
)


# ------------------------------------------------------------
# 9. MISSING HISTORY FLAGS
# ------------------------------------------------------------

model["has_transaction_history"] = (
    model["transaction_count"]
    .fillna(0)
    .gt(0)
    .astype(int)
)

model["has_usage_history"] = (
    model["active_days"]
    .fillna(0)
    .gt(0)
    .astype(int)
)


# Numeric transaction fields:
transaction_zero_columns = [
    "transaction_count",
    "cancellation_count",
    "total_actual_amount_paid",
    "average_actual_amount_paid",
    "total_plan_list_price",
    "average_plan_list_price",
]

for col in transaction_zero_columns:
    model[col] = model[col].fillna(0)


# Numeric usage fields:
usage_zero_columns = [
    "active_days",
    "total_unique_songs",
    "total_listening_secs",
    "average_daily_listening_secs",
]

for col in usage_zero_columns:
    model[col] = model[col].fillna(0)


# ------------------------------------------------------------
# 10. FINAL VALIDATION
# ------------------------------------------------------------

print("\n8. FINAL VALIDATION")
print("-" * 78)

print(f"Final rows: {len(model):,}")
print(f"Final columns: {len(model.columns):,}")
print(f"Unique customers: {model['msno'].nunique():,}")

if len(model) != 7500:
    raise ValueError(
        f"Expected 7,500 rows, found {len(model):,}."
    )

if model["msno"].nunique() != 7500:
    raise ValueError(
        "Final dataset contains duplicate customers."
    )

if model["is_churn"].isna().any():
    raise ValueError(
        "Missing churn targets detected."
    )


# Leakage check — transactions
transaction_leakage = (
    model["latest_transaction_date"] >
    CUTOFF_DATE
).sum()

print(
    f"Transaction dates after cutoff: "
    f"{transaction_leakage}"
)

if transaction_leakage != 0:
    raise ValueError(
        "TRANSACTION LEAKAGE DETECTED."
    )


# Leakage check — usage
usage_leakage = (
    model["last_active_date"] >
    CUTOFF_DATE
).sum()

print(
    f"Usage dates after cutoff: "
    f"{usage_leakage}"
)

if usage_leakage != 0:
    raise ValueError(
        "USAGE LEAKAGE DETECTED."
    )


# ------------------------------------------------------------
# 11. SAVE
# ------------------------------------------------------------

model.to_csv(
    OUTPUT_FILE,
    index=False
)

print("\n9. SAVING OUTPUT")
print("-" * 78)

print(f"Saved: {OUTPUT_FILE}")
print(f"Rows: {len(model):,}")
print(f"Columns: {len(model.columns):,}")


# ------------------------------------------------------------
# 12. FINAL STATUS
# ------------------------------------------------------------

print("\n" + "=" * 78)
print("STEP 4 STATUS")
print("=" * 78)

print("7,500-customer sample: VERIFIED")
print("train_v2 target: VERIFIED")
print("Member features: CREATED")
print("Transaction features: CREATED")
print("Usage features: CREATED")
print("Prediction cutoff: 2017-02-28")
print("Transaction leakage: CHECKED")
print("Usage leakage: CHECKED")

print("\nNext step:")
print("Validate the leakage-safe model dataset.")