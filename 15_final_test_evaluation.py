from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "kkbox_leakage_safe_model_dataset.csv"
THRESHOLD_FILE = BASE_DIR / "selected_threshold.txt"
OUTPUT_FILE = BASE_DIR / "churn_model_final_metrics.csv"

SEED = 42
TEST_SIZE = 0.20
TARGET = "is_churn"
N_BOOT = 2000

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


threshold = float(THRESHOLD_FILE.read_text().strip())

df = pd.read_csv(INPUT_FILE)
X = df[CATEGORICAL_FEATURES + NUMERIC_FEATURES].copy()
y = df[TARGET].astype(int)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=TEST_SIZE, random_state=SEED, stratify=y
)
X_train = clean(X_train.reset_index(drop=True))
X_test = clean(X_test.reset_index(drop=True))
y_train = y_train.reset_index(drop=True).values
y_test = y_test.reset_index(drop=True).values
impute_recency(X_train, X_test)

model = build_model()
model.fit(X_train, y_train)
prob = model.predict_proba(X_test)[:, 1]
pred = (prob >= threshold).astype(int)

tn, fp, fn, tp = confusion_matrix(y_test, pred, labels=[0, 1]).ravel()
precision = tp / (tp + fp) if (tp + fp) else 0.0
recall = tp / (tp + fn)
base_rate = y_test.mean()

# Bootstrap 95% intervals (resampling test customers).
rng = np.random.default_rng(SEED)
n = len(y_test)
precs, recs = [], []
for _ in range(N_BOOT):
    idx = rng.integers(0, n, n)
    yt, pr = y_test[idx], pred[idx]
    t = int(((pr == 1) & (yt == 1)).sum())
    f = int(((pr == 1) & (yt == 0)).sum())
    pos = int((yt == 1).sum())
    if t + f > 0 and pos > 0:
        precs.append(t / (t + f))
        recs.append(t / pos)
p_lo, p_hi = np.percentile(precs, [2.5, 97.5])
r_lo, r_hi = np.percentile(recs, [2.5, 97.5])

print(f"Threshold (chosen on training data only): {threshold:.2f}")
print(f"Test customers: {n:,}   Test churners: {int(y_test.sum())}")
print(f"Test ROC-AUC: {roc_auc_score(y_test, prob):.4f}")
print(f"Confusion matrix  TN {tn}  FP {fp}  FN {fn}  TP {tp}")
print(f"Customers flagged: {tp + fp} of {n}")
print(f"Precision: {precision:.3f}  (95% CI {p_lo:.3f} to {p_hi:.3f})")
print(f"Recall:    {recall:.3f}  (95% CI {r_lo:.3f} to {r_hi:.3f})")
print(f"Baseline: flagging customers at random gives precision "
      f"{base_rate:.3f}; the model is {precision / base_rate:.1f}x better.")
print("Baseline: flagging no one gives recall 0.000.")

pd.DataFrame([{
    "threshold": threshold, "test_rows": n,
    "test_churners": int(y_test.sum()),
    "roc_auc": roc_auc_score(y_test, prob),
    "precision": precision, "precision_ci_low": p_lo,
    "precision_ci_high": p_hi,
    "recall": recall, "recall_ci_low": r_lo, "recall_ci_high": r_hi,
    "true_negatives": tn, "false_positives": fp,
    "false_negatives": fn, "true_positives": tp,
    "random_flag_precision": base_rate,
}]).to_csv(OUTPUT_FILE, index=False)
print(f"\nSaved: {OUTPUT_FILE.name}")