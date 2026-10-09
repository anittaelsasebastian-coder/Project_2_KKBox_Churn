"""
Project 2: Customer Churn & Retention Intelligence (KKBox)
02_sample_and_load.py

Purpose
-------
Takes the raw KKBox competition CSVs (downloaded separately from Kaggle —
this script does NOT fetch them), selects a random sample of customers who
have a real churn label, pulls ALL of their real transaction and usage-log
history (no truncation), and loads everything into the SQLite database
defined by 01_create_database.sql. No cleaning or recoding is applied here —
raw values load as-is.

Expected input files (place in --raw-dir)
------------------------------------------
    members_v3.csv       (source: Kaggle "kkbox-churn-prediction-challenge")
    train_v2.csv          -- use the v2 label file (final/corrected labels)
    transactions_v2.csv   -- use the v2 transactions file
    user_logs_v2.csv      -- use the v2 daily usage-log file

    Note: KKBox released this data in two phases, so both a base file
    (e.g. transactions.csv) and a "_v2" supplemental file exist for
    train/transactions/user_logs. This script uses the *_v2 files only,
    which is sufficient for a self-contained portfolio project. If you
    want deeper history, concatenate the base + _v2 files yourself before
    running this script (dedupe on the natural keys first).

Usage
-----
    python 02_sample_and_load.py \\
        --raw-dir ./raw_data \\
        --db-path ./kkbox_churn.db \\
        --ddl-path ./01_create_database.sql \\
        --sample-size 7500 \\
        --seed 42

Design notes
------------
- Sampling universe = members who ALSO appear in the label file (train_v2),
  so every sampled customer has a real, defined churn outcome.
- Once msno values are sampled, 100% of their rows are pulled from
  transactions and user_logs — never a random subset of a customer's history.
- All large files are read in chunks to avoid loading tens of millions of
  rows into memory at once; each chunk is filtered down to the sampled
  customers before being kept.
"""

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REQUIRED_FILES = {
    "members": "members_v3.csv",
    "train": "train_v2.csv",
    "transactions": "transactions_v2.csv",
    "user_logs": "user_logs_v2.csv",
}

CHUNKSIZE_DEFAULT = 2_000_000


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw-dir", required=True, type=Path,
                    help="Directory containing the raw KKBox CSVs")
    p.add_argument("--db-path", required=True, type=Path,
                    help="Path to the SQLite database to create/overwrite")
    p.add_argument("--ddl-path", default=Path("01_create_database.sql"), type=Path,
                    help="Path to the DDL script (default: ./01_create_database.sql)")
    p.add_argument("--sample-size", default=7500, type=int,
                    help="Number of customers to sample (default: 7500)")
    p.add_argument("--seed", default=42, type=int,
                    help="Random seed, for a reproducible sample (default: 42)")
    p.add_argument("--chunksize", default=CHUNKSIZE_DEFAULT, type=int,
                    help="Rows per chunk when scanning large files")
    return p.parse_args()


def check_files_exist(raw_dir: Path) -> dict:
    paths = {}
    missing = []
    for key, filename in REQUIRED_FILES.items():
        path = raw_dir / filename
        if not path.exists():
            missing.append(filename)
        paths[key] = path
    if missing:
        print("ERROR: missing required raw files in", raw_dir, file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        print("\nDownload these from the Kaggle competition page "
              "'kkbox-churn-prediction-challenge' and place them in --raw-dir.",
              file=sys.stderr)
        sys.exit(1)
    return paths


def build_sample_pool(members_path: Path, train_path: Path) -> pd.Series:
    """Return the msno values eligible for sampling: present in both
    members_v3 (has demographic data) and train_v2 (has a real label)."""
    # Only pull msno from members to keep this step lightweight; the full
    # member row is re-read later, only for the sampled customers.
    member_ids = set()
    for chunk in pd.read_csv(members_path, usecols=["msno"], chunksize=CHUNKSIZE_DEFAULT,
                              dtype=str):
        member_ids.update(chunk["msno"])

    train_df = pd.read_csv(train_path, dtype=str)
    train_df = train_df.drop_duplicates(subset="msno")

    eligible = train_df[train_df["msno"].isin(member_ids)]
    return eligible.set_index("msno")["is_churn"]


def sample_customers(labels: pd.Series, n: int, seed: int) -> pd.Series:
    if n > len(labels):
        print(f"WARNING: requested sample size {n} exceeds eligible pool "
              f"({len(labels)}). Using full pool instead.", file=sys.stderr)
        n = len(labels)
    sampled = labels.sample(n=n, random_state=seed)
    return sampled


def load_members_for_sample(members_path: Path, sample_msno: set, chunksize: int) -> pd.DataFrame:
    keep = []
    for chunk in pd.read_csv(members_path, chunksize=chunksize, dtype=str):
        keep.append(chunk[chunk["msno"].isin(sample_msno)])
    return pd.concat(keep, ignore_index=True)


def filter_large_file_for_sample(path: Path, sample_msno: set, chunksize: int,
                                  dtype=None) -> pd.DataFrame:
    keep = []
    rows_scanned = 0
    for chunk in pd.read_csv(path, chunksize=chunksize, dtype=dtype):
        rows_scanned += len(chunk)
        keep.append(chunk[chunk["msno"].isin(sample_msno)])
    result = pd.concat(keep, ignore_index=True) if keep else pd.DataFrame()
    print(f"  scanned {rows_scanned:,} rows in {path.name}, "
          f"kept {len(result):,} for sampled customers")
    return result


def main():
    args = parse_args()

    if not args.ddl_path.exists():
        print(f"ERROR: DDL file not found at {args.ddl_path}", file=sys.stderr)
        sys.exit(1)

    paths = check_files_exist(args.raw_dir)

    print(f"Step 1/6: building eligible sample pool "
          f"(members ∩ labeled customers) ...")
    labels = build_sample_pool(paths["members"], paths["train"])
    print(f"  eligible pool size: {len(labels):,} customers")

    print(f"Step 2/6: sampling {args.sample_size:,} customers "
          f"(seed={args.seed}) ...")
    sampled_labels = sample_customers(labels, args.sample_size, args.seed)
    sample_msno = set(sampled_labels.index)
    actual_n = len(sample_msno)
    print(f"  sampled: {actual_n:,} customers "
          f"({sampled_labels.astype(int).mean():.1%} churn rate in sample)")

    print("Step 3/6: pulling member rows for sampled customers ...")
    members_df = load_members_for_sample(paths["members"], sample_msno, args.chunksize)

    print("Step 4/6: pulling ALL transaction history for sampled customers ...")
    transactions_df = filter_large_file_for_sample(
        paths["transactions"], sample_msno, args.chunksize, dtype=str
    )

    print("Step 5/6: pulling ALL usage-log history for sampled customers ...")
    logs_df = filter_large_file_for_sample(
        paths["user_logs"], sample_msno, args.chunksize, dtype=str
    )

    print("Step 6/6: writing to SQLite ...")
    if args.db_path.exists():
        args.db_path.unlink()
    conn = sqlite3.connect(args.db_path)
    with open(args.ddl_path) as f:
        conn.executescript(f.read())

    members_df.to_sql("members", conn, if_exists="append", index=False)

    churn_df = sampled_labels.rename("is_churn").reset_index()
    churn_df["is_churn"] = churn_df["is_churn"].astype(int)
    churn_df.to_sql("churn_labels", conn, if_exists="append", index=False)

    # transaction_id is autoincrement — do not pass it in
    txn_cols = ["msno", "payment_method_id", "payment_plan_days", "plan_list_price",
                "actual_amount_paid", "is_auto_renew", "transaction_date",
                "membership_expire_date", "is_cancel"]
    transactions_df[txn_cols].to_sql("transactions", conn, if_exists="append", index=False)

    logs_df = logs_df.rename(columns={"date": "log_date"})
    log_cols = ["msno", "log_date", "num_25", "num_50", "num_75", "num_985",
                "num_100", "num_unq", "total_secs"]
    logs_df[log_cols].to_sql("user_logs_daily", conn, if_exists="append", index=False)

    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_sample_size": str(args.sample_size),
        "actual_sample_size": str(actual_n),
        "random_seed": str(args.seed),
        "source_members_file": REQUIRED_FILES["members"],
        "source_train_file": REQUIRED_FILES["train"],
        "source_transactions_file": REQUIRED_FILES["transactions"],
        "source_user_logs_file": REQUIRED_FILES["user_logs"],
        "sampling_rule": "random sample of msno present in both members_v3 "
                          "and train_v2; ALL transaction/log rows kept for "
                          "each sampled msno (no row-level truncation)",
    }
    conn.executemany(
        "INSERT INTO _sample_metadata (key, value) VALUES (?, ?)",
        list(metadata.items()),
    )
    conn.commit()

    print("\n=== VERIFICATION ===")
    cur = conn.cursor()
    for table in ["members", "churn_labels", "transactions", "user_logs_daily"]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"  {table}: {cur.fetchone()[0]:,} rows")

    cur.execute("SELECT COUNT(DISTINCT msno) FROM members")
    print(f"  distinct msno in members: {cur.fetchone()[0]:,}")

    cur.execute("""
        SELECT COUNT(*) FROM transactions t
        LEFT JOIN members m ON t.msno = m.msno
        WHERE m.msno IS NULL
    """)
    orphan_txn = cur.fetchone()[0]
    print(f"  orphan transaction rows (no matching member): {orphan_txn:,}"
          f"{'  [OK]' if orphan_txn == 0 else '  [CHECK THIS]'}")

    cur.execute("""
        SELECT COUNT(*) FROM user_logs_daily l
        LEFT JOIN members m ON l.msno = m.msno
        WHERE m.msno IS NULL
    """)
    orphan_logs = cur.fetchone()[0]
    print(f"  orphan log rows (no matching member): {orphan_logs:,}"
          f"{'  [OK]' if orphan_logs == 0 else '  [CHECK THIS]'}")

    cur.execute("""
        SELECT msno, log_date, COUNT(*) c FROM user_logs_daily
        GROUP BY msno, log_date HAVING c > 1
    """)
    dupe_logs = len(cur.fetchall())
    print(f"  duplicate (msno, log_date) pairs in logs: {dupe_logs:,}"
          f"{'  [OK]' if dupe_logs == 0 else '  [CHECK THIS]'}")

    cur.execute("SELECT COUNT(*) FROM members WHERE gender IS NULL")
    print(f"  members with NULL gender (expected, not an error): {cur.fetchone()[0]:,}")

    cur.execute("SELECT MIN(bd), MAX(bd) FROM members")
    bd_min, bd_max = cur.fetchone()
    print(f"  bd (age) raw range: {bd_min} to {bd_max}  "
          f"[expected to contain invalid values — NOT cleaned here]")

    cur.execute("SELECT COUNT(*) FROM churn_labels WHERE is_churn = 1")
    churned = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM churn_labels")
    total = cur.fetchone()[0]
    print(f"  sample churn rate: {churned:,} / {total:,} = {churned/total:.1%}")

    conn.close()
    print(f"\nDatabase written to: {args.db_path}")


if __name__ == "__main__":
    main()
