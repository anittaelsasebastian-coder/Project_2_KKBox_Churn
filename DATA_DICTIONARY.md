# Data Dictionary

The model dataset (`kkbox_leakage_safe_model_dataset.csv`) has 7,500 rows, one per sampled customer, and 33 columns. It contains customer identifiers, so it is not published. All features use data on or before the cutoff date, 2017-02-28.

## Model dataset

| Column | Meaning | Notes |
|---|---|---|
| msno | Customer identifier (hashed) | Never published |
| is_churn | 1 if the customer churned, 0 otherwise | Competition label: no new valid subscription within 30 days after membership expiry |
| city | City code | In the dataset, not a model feature |
| gender | Gender | Often missing |
| registered_via | Registration channel code | Model feature |
| registration_init_time | Registration date | Set to missing if after the cutoff |
| registration_days_before_cutoff | Days from registration to the cutoff | Model feature |
| age_group | Age band: 13-17, 18-24, 25-34, 35-44, 45-54, 55+, Unknown | Built from reported age; values outside 13 to 100 are Unknown. Raw age is not included |
| transaction_count | Number of transactions on or before the cutoff | Model feature |
| cancellation_count | Number of those transactions flagged as cancellations | |
| first_transaction_date | Date of the earliest transaction | |
| latest_transaction_date | Date of the latest transaction | Same-day ties: expiry date, then cancel flag, stable sort |
| total_actual_amount_paid | Sum of amounts paid | NTD |
| average_actual_amount_paid | Mean amount paid | Missing if no transaction history |
| total_plan_list_price | Sum of plan list prices | NTD |
| average_plan_list_price | Mean plan list price | Missing if no transaction history |
| latest_payment_method_id | Payment method of the latest transaction | Code |
| latest_payment_plan_days | Plan length of the latest transaction, in days | |
| latest_plan_list_price | List price of the latest transaction | NTD |
| latest_actual_amount_paid | Amount paid in the latest transaction | NTD |
| latest_is_auto_renew | 1 if the latest transaction had auto-renew on, 0 if manual | Model feature; missing if no history |
| latest_is_cancel | 1 if the latest transaction was a cancellation | |
| latest_membership_expire_date | Membership expiry date of the latest transaction | |
| days_since_latest_transaction | Cutoff date minus latest transaction date, in days | Model feature; target-proximal indicator |
| active_days | Number of distinct days with listening on or before the cutoff | All listening days, not a recent window. Model feature |
| total_unique_songs | Sum of daily unique-song counts | A sum of daily counts, so not a count of distinct songs overall |
| total_listening_secs | Total seconds listened | Rows with negative or missing seconds were removed |
| average_daily_listening_secs | Mean seconds per listening row | |
| first_active_date | Earliest listening date | |
| last_active_date | Latest listening date | |
| days_since_last_activity | Cutoff date minus last active date, in days | Model feature |
| has_transaction_history | 1 if the customer has at least one transaction on or before the cutoff | Model feature |
| has_usage_history | 1 if the customer has any listening on or before the cutoff | |

## Recent-listening features (tested, not in the final model)

Built by `18_build_recent_usage.py` into `model_dataset_recent_usage.csv` (customer-level, not published).

| Column | Meaning |
|---|---|
| active_days_last_7 | Distinct listening days in the 7 days up to the cutoff |
| active_days_last_30 | Distinct listening days in the 30 days up to the cutoff |
| listening_secs_last_30 | Seconds listened in those 30 days |
| unique_songs_last_30 | Sum of daily unique-song counts in those 30 days |
| active_days_prior_30 | Distinct listening days in the 30 days before that window |
| active_days_change_30 | active_days_last_30 minus active_days_prior_30 |

## Dashboard tables (`dashboard_outputs/`, summary only, no customer rows)

| Table | Contents |
|---|---|
| overall_kpis | Customers, churned customers and churn rate (%) |
| renewal_summary | Customers, churned and churn rate (%) by latest renewal type |
| recency_summary | The same, by days since latest transaction |
| engagement_summary | The same, by recent-listening group; the measure column says which measure |
| scenario_summary | Illustrative avoided churn events and gross revenue for 2, 5 and 10 point reductions, in NTD |
| model_metrics | Held-out test metrics at threshold 0.10, with 95% bootstrap intervals |
| confusion_matrix | Test-set counts of actual versus predicted outcomes |
| lift_by_decile | Churn rate, lift and cumulative churners captured by risk decile |

Every dashboard table also carries `cutoff_date` and `source_script` columns.

## Conventions
- Currency: NTD. Monthly-equivalent revenue is latest paid amount divided by plan days, times 30.
- Rates are percentages in the dashboard tables and fractions in `churn_model_final_metrics.csv`.
- Missing values are kept as missing, not set to zero, where zero would be misleading.