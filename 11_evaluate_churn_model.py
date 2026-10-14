
from pathlib import Path
import warnings

import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    precision_score,
    recall_score,
    f1_score,
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    classification_report,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

warnings.filterwarnings("ignore", category=UserWarning)

BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "kkbox_leakage_safe_model_dataset.csv"
OUTPUT_FILE = BASE_DIR / "churn_model_evaluation_metrics.csv"
PREDICTIONS_FILE = BASE_DIR / "churn_model_test_predictions.csv"
SEED = 42
TEST_SIZE = 0.20
TARGET = "is_churn"

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


def main():
    print("=" * 70)
    print("KKBOX — HELD-OUT CHURN MODEL EVALUATION")
    print("=" * 70)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Dataset not found: {INPUT_FILE}")

    df = pd.read_csv(INPUT_FILE)

    required = [TARGET, "msno"] + CATEGORICAL_FEATURES + NUMERIC_FEATURES
    missing = sorted(set(required) - set(df.columns))
    if missing:
        raise ValueError(f"Required columns missing: {missing}")

    if df["msno"].duplicated().any():
        raise ValueError("Duplicate customer IDs found.")

    if df[TARGET].isna().any():
        raise ValueError("Missing target values found.")

    if not set(df[TARGET].unique()).issubset({0, 1}):
        raise ValueError("Target must contain only 0 and 1.")

    X = df[CATEGORICAL_FEATURES + NUMERIC_FEATURES].copy()
    y = df[TARGET].astype(int).copy()
    customer_ids = df["msno"].copy()

    # Split before learning any imputation or scaling values.
    X_train, X_test, y_train, y_test, id_train, id_test = (
        train_test_split(
            X,
            y,
            customer_ids,
            test_size=TEST_SIZE,
            random_state=SEED,
            stratify=y,
        )
    )

    # Clean categorical data.
    for frame in (X_train, X_test):
        for col in CATEGORICAL_FEATURES:
            frame[col] = (
                frame[col]
                .fillna("Missing")
                .astype(str)
                .replace({"nan": "Missing", "None": "Missing"})
            )

    # Ensure numeric columns are numeric.
    for frame in (X_train, X_test):
        for col in NUMERIC_FEATURES:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")
            frame[col] = frame[col].replace(
                [np.inf, -np.inf], np.nan
            )

    # For recency, learn the median using training customers with
    # transaction history only. Apply that fixed value to test data.
    history_col = "has_transaction_history"
    recency_col = "days_since_latest_transaction"

    history_mask = X_train[history_col].eq(1)
    recency_median = X_train.loc[history_mask, recency_col].median()

    if pd.isna(recency_median):
        raise ValueError("Cannot impute recency from training history.")

    X_train[recency_col] = X_train[recency_col].fillna(recency_median)
    X_test[recency_col] = X_test[recency_col].fillna(recency_median)

    # Pipeline fits remaining imputation, encoding, and scaling on train only.
    categorical_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OneHotEncoder(handle_unknown="ignore")),
    ])

    numeric_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])

    preprocessing = ColumnTransformer([
        ("categorical", categorical_pipeline, CATEGORICAL_FEATURES),
        ("numeric", numeric_pipeline, NUMERIC_FEATURES),
    ])

    model = Pipeline([
        ("preprocessing", preprocessing),
        ("classifier", LogisticRegression(
            max_iter=2000,
            class_weight=None,
            random_state=SEED,
        )),
    ])

    print(f"\nTotal customers: {len(df):,}")
    print(f"Training customers: {len(X_train):,}")
    print(f"Test customers: {len(X_test):,}")
    print(f"Training churn rate: {y_train.mean():.2%}")
    print(f"Test churn rate: {y_test.mean():.2%}")
    print("\nFitting model on training data...")

    model.fit(X_train, y_train)

    probabilities = model.predict_proba(X_test)[:, 1]
    predictions = (probabilities >= 0.50).astype(int)

    tn, fp, fn, tp = confusion_matrix(
        y_test, predictions, labels=[0, 1]
    ).ravel()

    metrics = {
        "split": "stratified_80_20",
        "random_seed": SEED,
        "threshold": 0.50,
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "train_churn_rate": y_train.mean(),
        "test_churn_rate": y_test.mean(),
        "roc_auc": roc_auc_score(y_test, probabilities),
        "pr_auc_average_precision": average_precision_score(
            y_test, probabilities
        ),
        "accuracy": accuracy_score(y_test, predictions),
        "balanced_accuracy": balanced_accuracy_score(
            y_test, predictions
        ),
        "precision": precision_score(
            y_test, predictions, zero_division=0
        ),
        "recall": recall_score(
            y_test, predictions, zero_division=0
        ),
        "f1": f1_score(y_test, predictions, zero_division=0),
        "brier_score": brier_score_loss(y_test, probabilities),
        "true_negatives": tn,
        "false_positives": fp,
        "false_negatives": fn,
        "true_positives": tp,
        "majority_class_accuracy": max(
            y_test.mean(), 1 - y_test.mean()
        ),
    }

    pd.DataFrame([metrics]).to_csv(OUTPUT_FILE, index=False)

    predictions_df = pd.DataFrame({
        "msno": id_test.to_numpy(),
        "actual_is_churn": y_test.to_numpy(),
        "predicted_probability": probabilities,
        "predicted_is_churn_at_0_50": predictions,
    })
    predictions_df.to_csv(PREDICTIONS_FILE, index=False)

    print("\nHELD-OUT TEST RESULTS")
    print("-" * 70)
    for name, value in metrics.items():
        if isinstance(value, (float, np.floating)):
            print(f"{name}: {value:.4f}")
        else:
            print(f"{name}: {value}")

    print("\nClassification report at threshold 0.50:")
    print(classification_report(
        y_test, predictions, zero_division=0
    ))

    print(f"Metrics saved: {OUTPUT_FILE.name}")
    print(f"Test predictions saved: {PREDICTIONS_FILE.name}")

    print("\nIMPORTANT LIMITATIONS")
    print("- This is a random held-out split, not temporal validation.")
    print("- The test set is from the same labeled cohort.")
    print("- A 0.50 threshold may be unsuitable for a 9.48% churn rate.")
    print("- Test predictions contain customer IDs; do not publish them.")
    print("- Do not claim future-period performance from this evaluation.")


if __name__ == "__main__":
    main()
