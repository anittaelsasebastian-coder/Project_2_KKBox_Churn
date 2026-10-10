
"""
PROJECT 2 — KKBOX CHURN
STEP 6 — STATISTICAL ANALYSIS OF CHURN DRIVERS

Input:
    kkbox_leakage_safe_model_dataset.csv

Output:
    statistical_categorical_results.csv
    statistical_numeric_results.csv
    statistical_analysis_summary.txt
"""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, fisher_exact, mannwhitneyu
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import proportion_confint


# ------------------------------------------------------------
# 1. CONFIGURATION
# ------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "kkbox_leakage_safe_model_dataset.csv"

CATEGORICAL_OUTPUT = BASE_DIR / "statistical_categorical_results.csv"
NUMERIC_OUTPUT = BASE_DIR / "statistical_numeric_results.csv"
SUMMARY_OUTPUT = BASE_DIR / "statistical_analysis_summary.txt"

TARGET = "is_churn"

CATEGORICAL_FEATURES = [
    "city",
    "gender",
    "registered_via",
    "age_group",
    "has_transaction_history",
    "has_usage_history",
    "latest_is_auto_renew",
    "latest_is_cancel",
    "latest_payment_method_id",
    "latest_payment_plan_days",
]

NUMERIC_FEATURES = [
    "registration_days_before_cutoff",
    "transaction_count",
    "cancellation_count",
    "total_actual_amount_paid",
    "average_actual_amount_paid",
    "total_plan_list_price",
    "average_plan_list_price",
    "days_since_latest_transaction",
    "active_days",
    "total_unique_songs",
    "total_listening_secs",
    "average_daily_listening_secs",
    "days_since_last_activity",
]


# ------------------------------------------------------------
# 2. LOAD AND CHECK DATA
# ------------------------------------------------------------

print("=" * 70)
print("STEP 6 — STATISTICAL ANALYSIS")
print("=" * 70)

if not INPUT_FILE.exists():
    raise FileNotFoundError(f"Dataset not found: {INPUT_FILE}")

df = pd.read_csv(INPUT_FILE)

required_columns = {TARGET}
missing_columns = required_columns - set(df.columns)

if missing_columns:
    raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

if df[TARGET].isna().any():
    raise ValueError("Target contains missing values.")

if not set(df[TARGET].unique()).issubset({0, 1}):
    raise ValueError("Target must contain only 0 and 1.")

if df["msno"].duplicated().any():
    raise ValueError("Duplicate customer IDs found.")

churn_rate = df[TARGET].mean()

print(f"Customers: {len(df):,}")
print(f"Churned: {int(df[TARGET].sum()):,}")
print(f"Retained: {int((df[TARGET] == 0).sum()):,}")
print(f"Churn rate: {churn_rate:.2%}")


# ------------------------------------------------------------
# 3. CATEGORICAL ASSOCIATIONS
# ------------------------------------------------------------

categorical_results = []

for feature in CATEGORICAL_FEATURES:
    if feature not in df.columns:
        print(f"Skipping absent categorical feature: {feature}")
        continue

    data = df[[feature, TARGET]].copy()
    data[feature] = data[feature].fillna("Missing").astype(str)

    contingency = pd.crosstab(data[feature], data[TARGET])

    if contingency.shape[0] < 2 or contingency.shape[1] < 2:
        print(f"Skipping {feature}: insufficient category variation.")
        continue

    chi2, p_value, dof, expected = chi2_contingency(
        contingency,
        correction=False
    )

    n = contingency.to_numpy().sum()
    min_dimension = min(contingency.shape[0] - 1, contingency.shape[1] - 1)
    cramers_v = (
        np.sqrt(chi2 / (n * min_dimension))
        if min_dimension > 0 and n > 0
        else np.nan
    )

    small_expected = bool((expected < 5).any())

    categorical_results.append({
        "feature": feature,
        "customers": int(n),
        "categories": int(contingency.shape[0]),
        "chi_square": float(chi2),
        "degrees_of_freedom": int(dof),
        "p_value": float(p_value),
        "cramers_v": float(cramers_v),
        "any_expected_count_below_5": small_expected,
    })

    print(
        f"Categorical: {feature:35s} "
        f"p={p_value:.5g}, Cramer's V={cramers_v:.4f}"
    )


cat_results = pd.DataFrame(categorical_results)

if not cat_results.empty:
    cat_results["p_adjusted_bh"] = multipletests(
        cat_results["p_value"],
        method="fdr_bh"
    )[1]

    cat_results["significant_after_bh_0_05"] = (
        cat_results["p_adjusted_bh"] < 0.05
    )

    cat_results = cat_results.sort_values("p_adjusted_bh")
    cat_results.to_csv(CATEGORICAL_OUTPUT, index=False)


# ------------------------------------------------------------
# 4. NUMERIC ASSOCIATIONS
# ------------------------------------------------------------

numeric_results = []

for feature in NUMERIC_FEATURES:
    if feature not in df.columns:
        print(f"Skipping absent numeric feature: {feature}")
        continue

    churned = pd.to_numeric(
        df.loc[df[TARGET] == 1, feature],
        errors="coerce"
    ).dropna()

    retained = pd.to_numeric(
        df.loc[df[TARGET] == 0, feature],
        errors="coerce"
    ).dropna()

    if len(churned) < 2 or len(retained) < 2:
        print(f"Skipping {feature}: insufficient valid observations.")
        continue

    statistic, p_value = mannwhitneyu(
        churned,
        retained,
        alternative="two-sided"
    )

    # Probability that a random churned value exceeds a random retained value.
    probability_superiority = statistic / (len(churned) * len(retained))
    rank_biserial = 2 * probability_superiority - 1

    numeric_results.append({
        "feature": feature,
        "churned_n": int(len(churned)),
        "retained_n": int(len(retained)),
        "churned_median": float(churned.median()),
        "retained_median": float(retained.median()),
        "churned_mean": float(churned.mean()),
        "retained_mean": float(retained.mean()),
        "median_difference_churned_minus_retained": float(
            churned.median() - retained.median()
        ),
        "mann_whitney_u": float(statistic),
        "p_value": float(p_value),
        "rank_biserial_effect": float(rank_biserial),
    })

    print(
        f"Numeric: {feature:35s} "
        f"p={p_value:.5g}, rank-biserial={rank_biserial:.4f}"
    )


num_results = pd.DataFrame(numeric_results)

if not num_results.empty:
    num_results["p_adjusted_bh"] = multipletests(
        num_results["p_value"],
        method="fdr_bh"
    )[1]

    num_results["significant_after_bh_0_05"] = (
        num_results["p_adjusted_bh"] < 0.05
    )

    num_results = num_results.sort_values("p_adjusted_bh")
    num_results.to_csv(NUMERIC_OUTPUT, index=False)


# ------------------------------------------------------------
# 5. CHURN RATE CONFIDENCE INTERVAL
# ------------------------------------------------------------

churned_count = int(df[TARGET].sum())
total_count = len(df)

ci_low, ci_high = proportion_confint(
    count=churned_count,
    nobs=total_count,
    alpha=0.05,
    method="wilson"
)


# ------------------------------------------------------------
# 6. SAVE SUMMARY
# ------------------------------------------------------------

summary_lines = [
    "KKBOX CHURN — STATISTICAL ANALYSIS SUMMARY",
    "=" * 50,
    f"Customers analyzed: {total_count:,}",
    f"Churned customers: {churned_count:,}",
    f"Retained customers: {total_count - churned_count:,}",
    f"Observed churn rate: {churn_rate:.2%}",
    f"95% Wilson confidence interval: {ci_low:.2%} to {ci_high:.2%}",
    "",
    "METHODS",
    "- Categorical features: chi-square tests and Cramer's V.",
    "- Numeric features: Mann-Whitney U tests and rank-biserial effect.",
    "- Benjamini-Hochberg correction applied separately to each test family.",
    "",
    "INTERPRETATION LIMITS",
    "- Associations do not establish causation.",
    "- Small category counts can make chi-square results unreliable.",
    "- Results describe this 7,500-customer sample.",
    "- Features are tested individually; confounding is not controlled.",
    "- These results do not establish predictive performance.",
    "",
    "NEXT REVIEW",
    "Inspect category sizes, adjusted p-values, effect sizes, and missingness",
    "before drawing business conclusions.",
]

SUMMARY_OUTPUT.write_text("\n".join(summary_lines), encoding="utf-8")

print("\n" + "=" * 70)
print("STATISTICAL ANALYSIS COMPLETE")
print("=" * 70)
print(f"Categorical results: {CATEGORICAL_OUTPUT.name}")
print(f"Numeric results: {NUMERIC_OUTPUT.name}")
print(f"Summary: {SUMMARY_OUTPUT.name}")
print(f"Churn rate 95% CI: {ci_low:.2%} to {ci_high:.2%}")
