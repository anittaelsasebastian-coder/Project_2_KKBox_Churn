
from pathlib import Path
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests

warnings.filterwarnings("ignore", category=RuntimeWarning)

BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "kkbox_leakage_safe_model_dataset.csv"
OUTPUT_FILE = BASE_DIR / "logistic_regression_results.csv"
SUMMARY_FILE = BASE_DIR / "logistic_regression_summary.txt"

TARGET = "is_churn"

# Use only features intended to be available at the 2017-02-28 cutoff.
# Payment and engagement fields must already have been rebuilt from
# pre-cutoff transactions and usage logs.
CATEGORICAL_FEATURES = [
    "gender",
    "registered_via",
    "age_group",
    "latest_is_auto_renew",
]
NUMERIC_FEATURES = [
    "registration_days_before_cutoff",
    "transaction_count",
    "days_since_latest_transaction",
    "has_transaction_history",
    "active_days",
    "days_since_last_activity",
]

print("=" * 70)
print("KKBOX — EXPLANATORY LOGISTIC REGRESSION")
print("=" * 70)

if not INPUT_FILE.exists():
    raise FileNotFoundError(f"Dataset not found: {INPUT_FILE}")

df = pd.read_csv(INPUT_FILE)

if TARGET not in df.columns:
    raise ValueError(f"Target column missing: {TARGET}")

if df["msno"].duplicated().any():
    raise ValueError("Duplicate customers found.")

if df[TARGET].isna().any() or not set(df[TARGET].unique()).issubset({0, 1}):
    raise ValueError("Target must be complete and coded as 0/1.")

# Explicitly exclude dates, IDs, target-derived risk segments, and
# payment values that may be direct duplicates of other variables.
features = [
    f for f in CATEGORICAL_FEATURES + NUMERIC_FEATURES
    if f in df.columns
]

missing = sorted(
    set(CATEGORICAL_FEATURES + NUMERIC_FEATURES) - set(df.columns)
)
if missing:
    print("Features not found and therefore excluded:", missing)

if not features:
    raise ValueError("No eligible features found.")

# Check date fields as an additional audit; do not use dates directly.
for date_col in [
    "first_transaction_date",
    "latest_transaction_date",
    "latest_membership_expire_date",
    "first_active_date",
    "last_active_date",
]:
    if date_col in df.columns:
        print(f"Excluded raw date field: {date_col}")

print(f"\nRows: {len(df):,}")
print(f"Churned: {int(df[TARGET].sum()):,}")
print(f"Churn rate: {df[TARGET].mean():.2%}")
print("Candidate features:", ", ".join(features))

# Prepare a model table. Missing categorical values become an explicit
# category; missing numeric values use median imputation.
model_df = df[[TARGET] + features].copy()

for col in CATEGORICAL_FEATURES:
    if col in model_df.columns:
        model_df[col] = (
            model_df[col]
            .fillna("Missing")
            .astype(str)
            .replace({"nan": "Missing", "None": "Missing"})
        )
for col in NUMERIC_FEATURES:
    if col in model_df.columns:
        model_df[col] = pd.to_numeric(
            model_df[col], errors="coerce"
        )
        model_df[col] = model_df[col].replace(
            [np.inf, -np.inf], np.nan
        )

        
        if col == "days_since_latest_transaction":
            history_mask = (
                model_df["has_transaction_history"].eq(1)
                if "has_transaction_history" in model_df.columns
                else model_df[col].notna()
            )
            median = model_df.loc[history_mask, col].median()

            if pd.isna(median):
                raise ValueError(
                    "Cannot impute transaction recency: "
                    "no valid historical values."
                )

            model_df[col] = model_df[col].fillna(median)
        else:

            median = model_df[col].median()
            if pd.isna(median):
                print(f"Excluding all-missing numeric feature: {col}")
                model_df.drop(columns=[col], inplace=True)
            else:
                model_df[col] = model_df[col].fillna(median)
features = [f for f in features if f in model_df.columns]

# Exclude constant features.
features = [
    f for f in features
    if model_df[f].nunique(dropna=False) > 1
]

if not features:
    raise ValueError("No non-constant features remain.")

# Build formula with categorical encoding and continuous numeric features.
terms = []
for feature in features:
    if feature in CATEGORICAL_FEATURES:
        terms.append(f'C(Q("{feature}"))')
    else:
        terms.append(f'Q("{feature}")')

formula = f'{TARGET} ~ ' + " + ".join(terms)

print("\nFitting model. This may take a little time...")
print("Formula features:", len(features))

# Standard maximum-likelihood logistic regression.
# If rare categories cause separation or convergence failure, the script
# stops and reports the issue rather than silently changing the model.
try:
    model = smf.logit(formula=formula, data=model_df).fit(
        disp=False,
        maxiter=1000,
        method="newton"
    )
except Exception as exc:
    raise RuntimeError(
        "Logistic regression failed. Rare categories or separation may "
        "need to be addressed before interpreting results."
    ) from exc

if not model.mle_retvals.get("converged", False):
    raise RuntimeError(
        "Model did not converge. Do not interpret its coefficients."
    )
null_ll = (
    len(model_df)
    * (
        model_df[TARGET].mean()
        * np.log(model_df[TARGET].mean())
        + (1 - model_df[TARGET].mean())
        * np.log(1 - model_df[TARGET].mean())
    )
)

print(f"Full-model log-likelihood: {model.llf:.4f}")
print(f"Null-model log-likelihood: {null_ll:.4f}")
print(f"McFadden pseudo R-squared: {1 - model.llf / null_ll:.4f}")

if model.llf < null_ll - 1e-6:
    raise RuntimeError(
        "Full model fits worse than the intercept-only model. "
        "Do not interpret coefficients."
    )
params = model.params
conf = model.conf_int()
pvalues = model.pvalues

results = pd.DataFrame({
    "term": params.index,
    "coefficient_log_odds": params.values,
    "odds_ratio": np.exp(params.values),
    "ci_95_lower_or": np.exp(conf[0].values),
    "ci_95_upper_or": np.exp(conf[1].values),
    "p_value": pvalues.values,
})

# Correct for multiple coefficient tests, excluding the intercept.
mask = (
    (results["term"] != "Intercept")
    & results["p_value"].notna()
    & np.isfinite(results["p_value"])
)

results["p_adjusted_bh"] = np.nan

if mask.any():
    results.loc[mask, "p_adjusted_bh"] = multipletests(
        results.loc[mask, "p_value"].astype(float),
        method="fdr_bh"
    )[1]

results["significant_after_bh_0_05"] = (
    results["p_adjusted_bh"] < 0.05
)

results = results.sort_values(
    "p_adjusted_bh",
    na_position="last"
)
results.to_csv(OUTPUT_FILE, index=False)

summary = [
    "KKBOX EXPLANATORY LOGISTIC REGRESSION",
    "=" * 50,
    f"Rows analyzed: {len(model_df):,}",
    f"Churned: {int(model_df[TARGET].sum()):,}",
    f"Churn rate: {model_df[TARGET].mean():.2%}",
    f"Converged: {model.mle_retvals.get('converged', False)}",
    f"Features included: {len(features)}",
    f"Model log-likelihood: {model.llf:.4f}",
    f"AIC: {model.aic:.4f}",
    f"BIC: {model.bic:.4f}",
    f"Pseudo R-squared (McFadden): {model.prsquared:.4f}",
    "",
    "CAUTIONS",
    "- Odds ratios are adjusted associations, not causal effects.",
    "- Sparse categories can cause unstable estimates.",
    "- Median imputation and missing-category indicators affect interpretation.",
    "- Multiple-testing adjustment applies to coefficient tests.",
    "- This is not a validated predictive model.",
    "- Confirm every feature was constructed using data available by 2017-02-28.",
]

SUMMARY_FILE.write_text("\n".join(summary), encoding="utf-8")

print("\nMODEL FIT COMPLETE")
print(f"Converged: {model.mle_retvals.get('converged', False)}")
print(f"AIC: {model.aic:.2f}")
print(f"McFadden pseudo R-squared: {model.prsquared:.4f}")
print(f"Results saved: {OUTPUT_FILE.name}")
print(f"Summary saved: {SUMMARY_FILE.name}")

print("\nTop coefficient results:")
print(results.head(15).to_string(index=False))
