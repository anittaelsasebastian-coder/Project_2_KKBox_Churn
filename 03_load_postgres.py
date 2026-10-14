import pandas as pd
import psycopg2
import os
from pathlib import Path
from io import StringIO

# ============================================================
# SETTINGS
# ============================================================
RAW_DIR = Path("./raw_data")
SAMPLE_SIZE = 7500
SEED = 42

# ============================================================
# CONNECT TO POSTGRESQL
# ============================================================
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="kkbox_churn",
    user="postgres",
    password=os.getenv("POSTGRES_PASSWORD")
)

print("PostgreSQL connection successful.")

cursor = conn.cursor()

# ============================================================
# LOAD LABELS AND MEMBERS
# ============================================================
print("Loading train data...")

train = pd.read_csv(
    RAW_DIR / "train_v2.csv",
    usecols=["msno", "is_churn"]
)

members = pd.read_csv(
    RAW_DIR / "members_v3.csv"
)

# One churn label per customer
train = train.drop_duplicates(subset="msno")

# Customers available in BOTH datasets
eligible = set(members["msno"].dropna()).intersection(
    set(train["msno"].dropna())
)

print(f"Eligible customers: {len(eligible):,}")

# ============================================================
# SAMPLE 7,500 UNIQUE CUSTOMERS
# ============================================================
sample_pool = train[train["msno"].isin(eligible)]

sample_ids = set(
    sample_pool
    .sample(n=SAMPLE_SIZE, random_state=SEED)["msno"]
)

print(f"Sampled customers: {len(sample_ids):,}")

# ============================================================
# PREPARE MEMBERS
# ============================================================
members_sample = members[
    members["msno"].isin(sample_ids)
].copy()

# Convert registration date: YYYYMMDD -> YYYY-MM-DD
members_sample["registration_init_time"] = pd.to_datetime(
    members_sample["registration_init_time"],
    format="%Y%m%d",
    errors="coerce"
).dt.strftime("%Y-%m-%d")

# ============================================================
# PREPARE CHURN LABELS
# ============================================================
churn_labels = train[
    train["msno"].isin(sample_ids)
].copy()

# ============================================================
# LOAD TRANSACTIONS
# ============================================================
print("Loading transaction history...")

transaction_chunks = []

for chunk in pd.read_csv(
    RAW_DIR / "transactions_v2.csv",
    chunksize=200_000
):
    filtered = chunk[chunk["msno"].isin(sample_ids)]

    if not filtered.empty:
        transaction_chunks.append(filtered)

transactions = pd.concat(
    transaction_chunks,
    ignore_index=True
)

# Convert transaction dates
for col in ["transaction_date", "membership_expire_date"]:
    transactions[col] = pd.to_datetime(
        transactions[col],
        format="%Y%m%d",
        errors="coerce"
    ).dt.strftime("%Y-%m-%d")

print(f"Transactions kept: {len(transactions):,}")

# ============================================================
# LOAD USER LOGS
# ============================================================
print("Loading usage history...")

log_chunks = []

for chunk in pd.read_csv(
    RAW_DIR / "user_logs_v2.csv",
    chunksize=500_000
):
    filtered = chunk[chunk["msno"].isin(sample_ids)]

    if not filtered.empty:
        log_chunks.append(filtered)

user_logs = pd.concat(
    log_chunks,
    ignore_index=True
)

# Rename source column "date" to PostgreSQL column "log_date"
user_logs = user_logs.rename(
    columns={"date": "log_date"}
)

# Convert log date
user_logs["log_date"] = pd.to_datetime(
    user_logs["log_date"],
    format="%Y%m%d",
    errors="coerce"
).dt.strftime("%Y-%m-%d")

print(f"User logs kept: {len(user_logs):,}")

# ============================================================
# CLEAR EXISTING DATA
# ============================================================
print("Loading data into PostgreSQL...")

cursor.execute("""
TRUNCATE TABLE
    user_logs_daily,
    transactions,
    churn_labels,
    members
RESTART IDENTITY;
""")

# ============================================================
# COPY DATAFRAME INTO POSTGRESQL
# ============================================================
def copy_dataframe(df, table_name):
    buffer = StringIO()

    df.to_csv(
        buffer,
        index=False,
        header=False,
        na_rep=""
    )

    buffer.seek(0)

    columns = ",".join(df.columns)

    cursor.copy_expert(
        f"""
        COPY {table_name} ({columns})
        FROM STDIN
        WITH (
            FORMAT CSV,
            NULL ''
        )
        """,
        buffer
    )

# ============================================================
# LOAD MEMBERS
# ============================================================
copy_dataframe(
    members_sample[
        [
            "msno",
            "city",
            "bd",
            "gender",
            "registered_via",
            "registration_init_time"
        ]
    ],
    "members"
)

# ============================================================
# LOAD CHURN LABELS
# ============================================================
copy_dataframe(
    churn_labels[
        ["msno", "is_churn"]
    ],
    "churn_labels"
)

# ============================================================
# LOAD TRANSACTIONS
# ============================================================
transactions = transactions.reset_index(drop=True)

transactions.insert(
    0,
    "transaction_id",
    range(1, len(transactions) + 1)
)

copy_dataframe(
    transactions[
        [
            "transaction_id",
            "msno",
            "payment_method_id",
            "payment_plan_days",
            "plan_list_price",
            "actual_amount_paid",
            "is_auto_renew",
            "transaction_date",
            "membership_expire_date",
            "is_cancel"
        ]
    ],
    "transactions"
)

# ============================================================
# LOAD USER LOGS
# ============================================================
copy_dataframe(
    user_logs[
        [
            "msno",
            "log_date",
            "num_25",
            "num_50",
            "num_75",
            "num_985",
            "num_100",
            "num_unq",
            "total_secs"
        ]
    ],
    "user_logs_daily"
)

# ============================================================
# SAMPLE METADATA
# ============================================================
cursor.execute("""
INSERT INTO _sample_metadata
    (sample_id, sample_size, seed)
VALUES
    (1, %s, %s)
ON CONFLICT (sample_id)
DO UPDATE SET
    sample_size = EXCLUDED.sample_size,
    seed = EXCLUDED.seed,
    created_at = CURRENT_TIMESTAMP;
""", (len(sample_ids), SEED))

# ============================================================
# COMMIT
# ============================================================
conn.commit()

print("Data successfully loaded into PostgreSQL.")

# ============================================================
# VERIFY
# ============================================================
for table in [
    "members",
    "churn_labels",
    "transactions",
    "user_logs_daily"
]:
    cursor.execute(
        f"SELECT COUNT(*) FROM {table};"
    )

    count = cursor.fetchone()[0]

    print(f"{table}: {count:,}")

cursor.close()
conn.close()

print("Done.")