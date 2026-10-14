from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "kkbox_leakage_safe_model_dataset.csv"
THRESHOLD_FILE = BASE_DIR / "selected_threshold.txt"

SEED = 42
TEST_SIZE = 0.20
TARGET = "is_churn"
MIN_PRECISION = 0.40
N_FOLDS = 5

CATEGORICAL_FEATURES = [
    "gender", "registered_via", "age_group", "latest_is_auto_renew",
]
NUMERIC_FEATURES = [
    "registration_days_before_cutoff", "transaction_count",
    "days_since_latest_transaction", "has_transaction_history",
    "active_days", "days_since_last_activity",
]


def clean(frame):
    for col in CATEGORICAL_FEATURES:
        frame[col] = (
            frame[col].fillna("Missing").astype(str)
            .replace({"nan": "Missing", "None": "Missing"})
        )
    for col in NUMERIC_FEATURES:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
        frame[col] = frame[col].replace([np.inf, -np.inf], np.nan)
    return frame


def impute_recency(train, other):
    col = "days_since_latest_transaction"
    median = train.loc[train["has_transaction_history"].eq(1), col].median()
    if pd.isna(median):
        raise ValueError("Cannot impute recency from training history.")
    train[col] = train[col].fillna(median)
    other[col] = other[col].fillna(median)


def build_model():
    categorical = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OneHotEncoder(handle_unknown="ignore")),
    ])
    numeric = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    prep = ColumnTransformer([
        ("categorical", categorical, CATEGORICAL_FEATURES),
        ("numeric", numeric, NUMERIC_FEATURES),
    ])
    return Pipeline([
        ("preprocessing", prep),
        ("classifier", LogisticRegression(
            max_iter=2000, class_weight=None, random_state=SEED)),
    ])


df = pd.read_csv(INPUT_FILE)
X = df[CATEGORICAL_FEATURES + NUMERIC_FEATURES].copy()
y = df[TARGET].astype(int)

# Same split as 11_evaluate_churn_model.py. The test set is thrown away here.
X_train, _X_test, y_train, _y_test = train_test_split(
    X, y, test_size=TEST_SIZE, random_state=SEED, stratify=y
)
X_train = clean(X_train.reset_index(drop=True))
y_train = y_train.reset_index(drop=True)

# Out-of-fold predictions: each training customer is scored by a model
# that never saw that customer.
oof = np.zeros(len(X_train))
skf = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
for fit_idx, val_idx in skf.split(X_train, y_train):
    X_fit = X_train.iloc[fit_idx].copy()
    X_val = X_train.iloc[val_idx].copy()
    impute_recency(X_fit, X_val)
    model = build_model()
    model.fit(X_fit, y_train.iloc[fit_idx])
    oof[val_idx] = model.predict_proba(X_val)[:, 1]

print(f"Training customers: {len(X_train):,}")
print(f"Training churners: {int(y_train.sum()):,}")
print(f"Out-of-fold ROC-AUC: {roc_auc_score(y_train, oof):.4f}")

rows = []
for t in np.arange(0.02, 0.96, 0.01):
    flagged = oof >= t
    n_flagged = int(flagged.sum())
    tp = int((flagged & (y_train.values == 1)).sum())
    precision = tp / n_flagged if n_flagged else 0.0
    recall = tp / int(y_train.sum())
    rows.append((round(float(t), 2), n_flagged, precision, recall))

table = pd.DataFrame(
    rows, columns=["threshold", "flagged", "precision", "recall"]
)

print("\nOut-of-fold results (every 0.05):")
print(table[(table["threshold"] * 100).round().astype(int) % 5 == 0]
      .round(3).to_string(index=False))

ok = table[table["precision"] >= MIN_PRECISION]
if ok.empty:
    raise ValueError(f"No threshold reaches precision {MIN_PRECISION}.")

best = ok.sort_values(["recall", "threshold"],
                      ascending=[False, False]).iloc[0]
print(f"\nRule: precision >= {MIN_PRECISION}, then maximize recall.")
print(f"Selected threshold: {best['threshold']:.2f}")
print(f"Out-of-fold precision: {best['precision']:.3f}")
print(f"Out-of-fold recall: {best['recall']:.3f}")
print(f"Customers flagged: {int(best['flagged'])} of {len(X_train)}")

THRESHOLD_FILE.write_text(f"{best['threshold']:.2f}\n")
print(f"\nSaved: {THRESHOLD_FILE.name}")