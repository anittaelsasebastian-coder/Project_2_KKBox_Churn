# Data Provenance and Reproducibility Notes

## Sources
- Sample: 7,500 customers drawn with seed 42 (`02_sample_and_load.py`).
- Raw files in `raw_data/` (not published): `members_v3.csv`, `train_v2.csv`, `transactions.csv`, `user_logs.csv`.
- Prediction cutoff: 2017-02-28. Only transactions and listening rows on or before the cutoff are used as features.

## Current dataset
- Built by `06_build_model_dataset.py` from the full `transactions.csv` (21,547,746 data rows) and `user_logs.csv`.
- Output: 7,500 rows, 33 columns, 711 churners (9.48%).
- Latest transaction per customer is selected by transaction date, then membership expiry date, then cancel flag, using a stable sort. Earlier versions did not break same-day ties, which changed 54 customers' latest-transaction fields.

## Known discrepancy: customers without transaction history
- In the current `raw_data/transactions.csv`, 7,485 of 7,500 sample customers have at least one transaction row. 15 have none (6 churners, 40.00%). The group is too small for conclusions.
- An earlier audit reported 133 customers without pre-cutoff history. This could not be reproduced: the file row count matches the earlier audit, and no tested cutoff date gave 133 (Jan 31: 231, Feb 1: 223, Feb 15: 126, Feb 28: 15).
- An older SQLite database built from `_v2` files showed 307 customers without transactions (79.48% churn). It used a different source, so its figures are not comparable.
- The cause of the difference is unknown. Neither source is declared authoritative.

## Figures from earlier versions that must not be reused
- Churn by renewal type, recency, usage, revenue and the revenue scenario were first computed from the `_v2` database. They were rebuilt from the current dataset (`16_rebuild_kpis.py`).
- "Active days" now counts all listening days up to the cutoff, not a short recent window, so it cannot be compared with older values.
- The monthly-equivalent revenue formula is latest paid amount / plan days x 30.

## Model evaluation
- Random stratified 80/20 split (seed 42): 6,000 train, 1,500 test. Not temporal validation, so no claim is made about future performance.
- Threshold 0.10 was chosen on out-of-fold training predictions only (`14_select_threshold.py`), then evaluated once on the test set (`15_final_test_evaluation.py`).
- Test result: precision 0.421 (95% CI 0.354 to 0.487), recall 0.655 (95% CI 0.578 to 0.731), ROC-AUC 0.8191.
- The explanatory regression and the evaluation script changed together (recency imputation and a history flag), so differences from earlier runs cannot be credited to the tie-break fix alone.

## Privacy
- Customer-level files (raw data, model dataset, predictions) are ignored by Git and never published.
- A database password was once committed. It was rotated, and the code now reads `POSTGRES_PASSWORD` from the environment.