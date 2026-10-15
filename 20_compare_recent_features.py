from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

BASE_DIR = Path(__file__).resolve().parent
SEED = 42
TARGET = "is_churn"

CAT = ["gender", "registered_via", "age_group", "latest_is_auto_renew"]
NUM = [
    "registration_days_before_cutoff", "transaction_count",
    "days_since_latest_transaction", "has_transaction_history",
    "active_days", "days_since_last_activity",
]
RECENT = [
    "active_days_last_7", "active_days_last_30",
    "listening_secs_last_30", "active_days_change_30",
]


def clean(frame):
    for col in CAT:
        frame[col] = (
            frame[col].fillna("Missing").astype(str)
            .replace({"nan": "Missing", "None": "Missing"})
        )
    for col in NUM + RECENT:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
        frame[col] = frame[col].replace([np.inf, -np.inf], np.nan)
    return frame


def build_model(num_cols):
    cat = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OneHotEncoder(handle_unknown="ignore")),
    ])
    num = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    prep = ColumnTransformer([("c", cat, CAT), ("n", num, num_cols)])
    return Pipeline([
        ("prep", prep),
        ("clf", LogisticRegression(max_iter=2000, random_state=SEED)),
    ])


def cv_scores(X, y, num_cols, seed):
    oof = np.zeros(len(X))
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    for fit_idx, val_idx in skf.split(X, y):
        X_fit = X.iloc[fit_idx].copy()
        X_val = X.iloc[val_idx].copy()
        col = "days_since_latest_transaction"
        med = X_fit.loc[X_fit["has_transaction_history"].eq(1), col].median()
        X_fit[col] = X_fit[col].fillna(med)
        X_val[col] = X_val[col].fillna(med)
        model = build_model(num_cols)
        model.fit(X_fit[CAT + num_cols], y.iloc[fit_idx])
        oof[val_idx] = model.predict_proba(X_val[CAT + num_cols])[:, 1]
    return roc_auc_score(y, oof), average_precision_score(y, oof)


base = pd.read_csv(BASE_DIR / "kkbox_leakage_safe_model_dataset.csv")
recent = pd.read_csv(BASE_DIR / "model_dataset_recent_usage.csv")
df = base.merge(recent, on="msno", how="left", validate="one_to_one")
assert len(df) == 7500

X = df[CAT + NUM + RECENT].copy()
y = df[TARGET].astype(int)

# Same split as the earlier scripts. The test set is not used here.
X_train, _X_test, y_train, _y_test = train_test_split(
    X, y, test_size=0.20, random_state=SEED, stratify=y
)
X_train = clean(X_train.reset_index(drop=True))
y_train = y_train.reset_index(drop=True)

rows = []
for seed in [42, 43, 44]:
    a = cv_scores(X_train, y_train, NUM, seed)
    b = cv_scores(X_train, y_train, NUM + RECENT, seed)
    rows.append((seed, a[0], b[0], a[1], b[1]))

res = pd.DataFrame(
    rows,
    columns=["cv_seed", "auc_current", "auc_with_recent",
             "ap_current", "ap_with_recent"],
)
print(res.round(4).to_string(index=False))
print("\nMeans:")
print(res.drop(columns="cv_seed").mean().round(4).to_string())
print("\nMean change with recent features:")
print(f"  ROC-AUC: {(res['auc_with_recent'] - res['auc_current']).mean():+.4f}")
print(f"  Average precision: "
      f"{(res['ap_with_recent'] - res['ap_current']).mean():+.4f}")