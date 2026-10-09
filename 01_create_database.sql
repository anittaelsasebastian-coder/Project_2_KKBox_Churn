-- ============================================================================
-- Project 2: Customer Churn & Retention Intelligence (KKBox)
-- 01_create_database.sql
--
-- Purpose:
--   Defines the raw warehouse schema. This is a faithful mirror of the
--   source KKBox CSV columns, with ONE addition: a warehouse-generated
--   surrogate key on `transactions` (the source file has no natural
--   unique row identifier). No values are cleaned, recoded, or filtered
--   here — that happens later, in the SQL analysis layer, so the raw
--   load remains a defensible, re-runnable source of truth.
--
-- Known raw-data quirks (intentionally NOT fixed at load time):
--   - members.bd (age) contains invalid values: negatives, 0, and
--     implausible outliers (e.g. > 100). Left as-is.
--   - members.gender is nullable (many users never set it).
--   - All *_date / *_time columns are loaded as TEXT in their native
--     YYYYMMDD form, not cast to DATE, so the raw table matches the
--     source byte-for-byte. Casting happens in the analysis views.
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------------------
-- members: one row per sampled customer (demographics + signup info)
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS members;
CREATE TABLE members (
    msno                    TEXT PRIMARY KEY,   -- anonymized user id (source key)
    city                    INTEGER,             -- encoded city code
    bd                      INTEGER,             -- RAW age field — known bad values, not cleaned here
    gender                  TEXT,                -- 'male' | 'female' | NULL
    registered_via          INTEGER,             -- encoded registration channel
    registration_init_time  TEXT                 -- raw YYYYMMDD as sourced
);

-- ----------------------------------------------------------------------------
-- transactions: full subscription/payment history for sampled customers
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS transactions;
CREATE TABLE transactions (
    transaction_id          INTEGER PRIMARY KEY AUTOINCREMENT,  -- WAREHOUSE-GENERATED
                                                                  -- surrogate key. NOT an
                                                                  -- original KKBox field —
                                                                  -- the source has no row id.
    msno                    TEXT NOT NULL,
    payment_method_id       INTEGER,
    payment_plan_days       INTEGER,
    plan_list_price         INTEGER,
    actual_amount_paid      INTEGER,
    is_auto_renew           INTEGER,             -- 0/1
    transaction_date        TEXT,                -- raw YYYYMMDD
    membership_expire_date  TEXT,                -- raw YYYYMMDD
    is_cancel               INTEGER,             -- 0/1, this transaction was a cancellation
    FOREIGN KEY (msno) REFERENCES members(msno)
);
CREATE INDEX idx_transactions_msno ON transactions(msno);
CREATE INDEX idx_transactions_date ON transactions(transaction_date);

-- ----------------------------------------------------------------------------
-- user_logs_daily: daily engagement, one row per customer per active day
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS user_logs_daily;
CREATE TABLE user_logs_daily (
    msno        TEXT NOT NULL,
    log_date    TEXT NOT NULL,      -- raw YYYYMMDD
    num_25      INTEGER,            -- songs played to <25% completion
    num_50      INTEGER,            -- 25-50%
    num_75      INTEGER,            -- 50-75%
    num_985     INTEGER,            -- 75-98.5%
    num_100     INTEGER,            -- finished (>=98.5%)
    num_unq     INTEGER,            -- unique songs played that day
    total_secs  REAL,               -- total seconds played that day
    PRIMARY KEY (msno, log_date),
    FOREIGN KEY (msno) REFERENCES members(msno)
);
CREATE INDEX idx_logs_msno ON user_logs_daily(msno);
CREATE INDEX idx_logs_date ON user_logs_daily(log_date);

-- ----------------------------------------------------------------------------
-- churn_labels: target variable, one row per sampled customer
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS churn_labels;
CREATE TABLE churn_labels (
    msno      TEXT PRIMARY KEY,
    is_churn  INTEGER NOT NULL,     -- 1 = no valid renewal within 30 days of
                                     -- membership_expire_date; 0 = renewed
    FOREIGN KEY (msno) REFERENCES members(msno)
);

-- ----------------------------------------------------------------------------
-- _sample_metadata: records exactly how this sample/load was generated,
-- so the database is self-documenting and reproducible.
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS _sample_metadata;
CREATE TABLE _sample_metadata (
    key    TEXT PRIMARY KEY,
    value  TEXT
);
