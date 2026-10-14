from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
CUTOFF = pd.Timestamp("2017-02-28")

sample = pd.read_csv(
    BASE_DIR / "Project_2_KKBox_Churn_Analysis.csv", usecols=["msno"]
)
ids = set(sample["msno"].astype(str).str.lstrip("'"))

parts = []
for chunk in pd.read_csv(
    BASE_DIR / "raw_data" / "transactions.csv",
    usecols=["msno", "transaction_date"],
    chunksize=250_000,
):
    chunk["msno"] = chunk["msno"].astype(str).str.lstrip("'")
    chunk = chunk[chunk["msno"].isin(ids)].copy()
    if chunk.empty:
        continue
    chunk["d"] = pd.to_datetime(
        chunk["transaction_date"].astype(str), format="%Y%m%d", errors="coerce"
    )
    parts.append(chunk.groupby("msno")["d"].min())

earliest = pd.concat(parts).groupby(level=0).min()

print(f"Sample customers: {len(ids):,}")
print(f"With any transaction row: {len(earliest):,}")
print(f"Earliest date on or before cutoff: {(earliest <= CUTOFF).sum():,}")
print(f"Earliest date before cutoff: {(earliest < CUTOFF).sum():,}")
print(f"Earliest date unreadable: {int(earliest.isna().sum()):,}")

print("\nCustomers with a first transaction on or before each date:")
for d in ["2017-01-31", "2017-02-01", "2017-02-15", "2017-02-28"]:
    n_ok = int((earliest <= pd.Timestamp(d)).sum())
    print(f"  {d}: {n_ok:,}  (without: {len(ids) - n_ok:,})")