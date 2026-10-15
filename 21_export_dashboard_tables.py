from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "dashboard_outputs"
OUT_DIR.mkdir(exist_ok=True)
CUTOFF = "2017-02-28"
SEED = 42

CAT = ["gender", "registered_via", "age_group", "latest_is_auto_renew"]
NUM = [
    "registration_days_before_cutoff", "transaction_count",
    "days_since_latest_transaction", "has_transaction_history",
    "active_days", "days_since_last_activity",
]

base = pd.read_csv(BASE_DIR / "kkbox_leakage_safe_model_dataset.csv")
recent = pd.read_csv(BASE_DIR / "model_dataset_recent_usage.csv")
df = base.merge(recent, on="msno", how="left", validate="one_to_one")
assert len(df) == 7500


def save(table, name, source):
    table = table.copy()
    table["cutoff_date"] = CUTOFF
    table["source_script"] = source
    assert "msno" not in table.columns, f"Customer IDs found in {name}"
    table.to_csv(OUT_DIR / name, index=False)
    print(f"Saved {name}: {len(table)} rows")


def churn_table(frame, col, label):
    t = frame.groupby(col, observed=True)["is_churn"].agg(
        customers="count", churned="sum", churn_rate_pct="mean"
    ).reset_index().rename(columns={col: label})
    t["churn_rate_pct"] = (t["churn_rate_pct"] * 100).round(2)
    return t


SRC = "21_export_dashboard_tables.py"

# 1. Overall KPIs
n, ch = len(df), int(df["is_churn"].sum())
save(pd.DataFrame([
    {"metric": "customers", "value": n},
    {"metric": "churned_customers", "value": ch},
    {"metric": "churn_rate_pct", "value": round(ch / n * 100, 2)},
]), "overall_kpis.csv", SRC)

# 2. Renewal type
df["renewal_type"] = df["latest_is_auto_renew"].map(
    {1: "auto-renew", 0: "manual-renew"}).fillna("no transaction history")
save(churn_table(df, "renewal_type", "group"), "renewal_summary.csv", SRC)

# 3. Recency (target-proximal indicator)
df["recency_group"] = pd.cut(
    df["days_since_latest_transaction"], bins=[-1, 7, 30, np.inf],
    labels=["0-7 days", "8-30 days", "31+ days"]).astype(object)
df.loc[df["has_transaction_history"] == 0, "recency_group"] = "no history"
save(churn_table(df, "recency_group", "group"), "recency_summary.csv", SRC)

# 4. Engagement
df["active_days_30_band"] = pd.cut(
    df["active_days_last_30"], bins=[-1, 0, 7, 14, 21, 30],
    labels=["0 days", "1-7", "8-14", "15-21", "22-30"])
df["change_vs_prior_30"] = pd.cut(
    df["active_days_change_30"], bins=[-31, -8, -1, 0, 7, 31],
    labels=["fell 8+", "fell 1-7", "no change", "rose 1-7", "rose 8+"])
eng = pd.concat([
    churn_table(df, "active_days_30_band", "group").assign(
        measure="active days in last 30"),
    churn_table(df, "change_vs_prior_30", "group").assign(
        measure="change vs prior 30 days"),
])
save(eng, "engagement_summary.csv", SRC)

# 5. Scenario (gross, illustrative, before intervention cost)
valid = df["latest_payment_plan_days"] > 0
df["monthly_revenue"] = np.where(
    valid, df["latest_actual_amount_paid"]
    / df["latest_payment_plan_days"] * 30, np.nan)
manual = df[df["renewal_type"] == "manual-renew"]
rev = manual.loc[manual["is_churn"] == 1, "monthly_revenue"].mean()
rows = []
for pts in [2, 5, 10]:
    avoided = len(manual) * pts / 100
    rows.append({
        "churn_reduction_points": pts,
        "manual_renew_customers": len(manual),
        "illustrative_avoided_churn_events": round(avoided, 2),
        "avg_monthly_revenue_churned_manual": round(rev, 2),
        "gross_monthly_revenue_scenario": round(avoided * rev, 2),
        "gross_annualized_scenario": round(avoided * rev * 12, 2),
        "note": "Illustrative, before intervention cost, not a forecast",
    })
save(pd.DataFrame(rows), "scenario_summary.csv", SRC)

# 6. Model metrics and confusion matrix (from the one final evaluation)
m = pd.read_csv(BASE_DIR / "churn_model_final_metrics.csv").iloc[0]
metrics = [
    ("threshold", m["threshold"]), ("roc_auc", m["roc_auc"]),
    ("precision", m["precision"]),
    ("precision_ci_low", m["precision_ci_low"]),
    ("precision_ci_high", m["precision_ci_high"]),
    ("recall", m["recall"]), ("recall_ci_low", m["recall_ci_low"]),
    ("recall_ci_high", m["recall_ci_high"]),
    ("test_churn_rate", m["random_flag_precision"]),
]
save(pd.DataFrame(metrics, columns=["metric", "value"]).round(4),
     "model_metrics.csv", "15_final_test_evaluation.py")
save(pd.DataFrame([
    {"actual": "retained", "predicted": "retained",
     "customers": int(m["true_negatives"])},
    {"actual": "retained", "predicted": "flagged",
     "customers": int(m["false_positives"])},
    {"actual": "churned", "predicted": "retained",
     "customers": int(m["false_negatives"])},
    {"actual": "churned", "predicted": "flagged",
     "customers": int(m["true_positives"])},
]), "confusion_matrix.csv", "15_final_test_evaluation.py")

# 7. Lift by risk decile (same model and split as the final evaluation).
# Descriptive only: nothing is tuned using the test set.
X = df[CAT + NUM].copy()
y = df["is_churn"].astype(int)
X_tr, X_te, y_tr, y_te = train_test_split(
    X, y, test_size=0.20, random_state=SEED, stratify=y)
for frame in (X_tr, X_te):
    for c in CAT:
        frame[c] = frame[c].fillna("Missing").astype(str).replace(
            {"nan": "Missing", "None": "Missing"})
    for c in NUM:
        frame[c] = pd.to_numeric(frame[c], errors="coerce").replace(
            [np.inf, -np.inf], np.nan)
col = "days_since_latest_transaction"
med = X_tr.loc[X_tr["has_transaction_history"].eq(1), col].median()
X_tr[col] = X_tr[col].fillna(med)
X_te[col] = X_te[col].fillna(med)
cat = Pipeline([("i", SimpleImputer(strategy="most_frequent")),
                ("e", OneHotEncoder(handle_unknown="ignore"))])
num = Pipeline([("i", SimpleImputer(strategy="median")),
                ("s", StandardScaler())])
model = Pipeline([
    ("p", ColumnTransformer([("c", cat, CAT), ("n", num, NUM)])),
    ("m", LogisticRegression(max_iter=2000, random_state=SEED)),
])
model.fit(X_tr, y_tr)
prob = model.predict_proba(X_te)[:, 1]
rank = pd.Series(prob).rank(method="first", ascending=False)
decile = pd.qcut(rank, 10, labels=range(1, 11)).astype(int)
t = pd.DataFrame({"risk_decile": decile.values, "churn": y_te.values})
g = t.groupby("risk_decile")["churn"].agg(
    customers="count", churned="sum").reset_index()
base_rate = y_te.mean()
g["churn_rate_pct"] = (g["churned"] / g["customers"] * 100).round(2)
g["lift_vs_average"] = ((g["churned"] / g["customers"])
                        / base_rate).round(2)
g["cumulative_churners_captured_pct"] = (
    g["churned"].cumsum() / g["churned"].sum() * 100).round(1)
save(g, "lift_by_decile.csv", SRC)

print("\nDone. Tables are in dashboard_outputs/ (no customer IDs).")