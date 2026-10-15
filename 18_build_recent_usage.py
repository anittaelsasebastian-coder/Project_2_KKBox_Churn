from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
CUTOFF = pd.Timestamp("2017-02-28")
START_7 = CUTOFF - pd.Timedelta(days=6)
START_30 = CUTOFF - pd.Timedelta(days=29)
START_PRIOR = CUTOFF - pd.Timedelta(days=59)
OUTPUT_FILE = BASE_DIR / "model_dataset_recent_usage.csv"

sample = pd.read_csv(
    BASE_DIR / "kkbox_leakage_safe_model_dataset.csv", usecols=["msno"]
)
ids = set(sample["msno"].astype(str).str.lstrip("'"))

parts = []
for chunk in pd.read_csv(
    BASE_DIR / "raw_data" / "user_logs.csv",
    usecols=["msno", "date", "num_unq", "total_secs"],
    chunksize=250_000,
):
    chunk["msno"] = chunk["msno"].astype(str).str.lstrip("'")
    chunk = chunk[chunk["msno"].isin(ids)].copy()
    if chunk.empty:
        continue
    chunk["date"] = pd.to_datetime(
        chunk["date"].astype(str), format="%Y%m%d", errors="coerce"
    )
    chunk["total_secs"] = pd.to_numeric(chunk["total_secs"], errors="coerce")
    chunk["num_unq"] = pd.to_numeric(chunk["num_unq"], errors="coerce")
    chunk = chunk[
        (chunk["date"] >= START_PRIOR)
        & (chunk["date"] <= CUTOFF)
        & chunk["total_secs"].notna()
        & (chunk["total_secs"] >= 0)
    ]
    if not chunk.empty:
        parts.append(chunk)

logs = pd.concat(parts, ignore_index=True)
print(f"Rows in the 60-day window: {len(logs):,}")

last30 = logs[logs["date"] >= START_30]
last7 = logs[logs["date"] >= START_7]
prior30 = logs[logs["date"] < START_30]

out = pd.DataFrame(index=sorted(ids))
out.index.name = "msno"
out["active_days_last_7"] = last7.groupby("msno")["date"].nunique()
out["active_days_last_30"] = last30.groupby("msno")["date"].nunique()
out["listening_secs_last_30"] = last30.groupby("msno")["total_secs"].sum()
out["unique_songs_last_30"] = last30.groupby("msno")["num_unq"].sum()
out["active_days_prior_30"] = prior30.groupby("msno")["date"].nunique()
out = out.fillna(0)
out["active_days_change_30"] = (
    out["active_days_last_30"] - out["active_days_prior_30"]
)

out.reset_index().to_csv(OUTPUT_FILE, index=False)

print(f"Customers: {len(out):,}")
print(f"With any listening in the last 30 days: "
      f"{int((out['active_days_last_30'] > 0).sum()):,}")
print(f"With no listening in the last 30 days: "
      f"{int((out['active_days_last_30'] == 0).sum()):,}")
print("\nAverages across customers:")
print(out.drop(columns=[]).mean().round(2).to_string())
print(f"\nSaved: {OUTPUT_FILE.name}")