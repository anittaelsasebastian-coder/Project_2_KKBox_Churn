"""Benchmark: does the churn model beat simple rules at the same contact budget?

Uses exactly the same split, cleaning and model as 15_final_test_evaluation.py.
Only aggregate results are saved. No customer-level output is written.
"""
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = BASE_DIR / "benchmark_model_vs_rules.csv"

# Reuse the settings and functions from script 15 so nothing can drift.
src = (BASE_DIR / "15_final_test_evaluation.py").read_text()
defs = src.split("threshold = float(")[0]          # definitions only, no run
ns = {"__file__": str(BASE_DIR / "15_final_test_evaluation.py")}
exec(defs, ns)

df = pd.read_csv(ns["INPUT_FILE"])
feats = ns["CATEGORICAL_FEATURES"] + ns["NUMERIC_FEATURES"]
X = df[feats].copy()
y = df[ns["TARGET"]].astype(int)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=ns["TEST_SIZE"], random_state=ns["SEED"], stratify=y)
X_train = ns["clean"](X_train.reset_index(drop=True))
X_test = ns["clean"](X_test.reset_index(drop=True))
y_train = y_train.reset_index(drop=True).values
y_test = y_test.reset_index(drop=True).values

# Rule inputs taken BEFORE recency imputation.
renew = X_test["latest_is_auto_renew"].str.strip().str.lower()
manual = renew.isin(["0", "0.0", "false"]).values
auto = renew.isin(["1", "1.0", "true"]).values
has_hist = X_test["has_transaction_history"].eq(1).values
lapsed = (has_hist & (X_test["days_since_latest_transaction"] >= 31)).values

ns["impute_recency"](X_train, X_test)
model = ns["build_model"]()
model.fit(X_train, y_train)
prob = model.predict_proba(X_test)[:, 1]
threshold = float(ns["THRESHOLD_FILE"].read_text().strip())

n, churners = len(y_test), int(y_test.sum())
order = np.argsort(-prob, kind="stable")


def summarise(name, flagged):
    k, tp = int(flagged.sum()), int((flagged & (y_test == 1)).sum())
    auto_ch = int((auto & (y_test == 1)).sum())
    auto_tp = int((flagged & auto & (y_test == 1)).sum())
    return {
        "approach": name, "customers_flagged": k,
        "share_contacted_pct": round(100 * k / n, 1),
        "churners_caught": tp,
        "precision_pct": round(100 * tp / k, 1) if k else 0.0,
        "churners_captured_pct": round(100 * tp / churners, 1),
        "auto_renew_churners_caught": f"{auto_tp} of {auto_ch}",
    }


def top_k(k):
    f = np.zeros(n, dtype=bool)
    f[order[:k]] = True
    return f


rows = []
for name, rule in [("Rule: manual-renew", manual),
                   ("Rule: manual-renew OR 31+ days lapsed", manual | lapsed)]:
    rows.append(summarise(name, rule))
    rows.append(summarise(f"Model, same budget as '{name[6:]}'",
                          top_k(int(rule.sum()))))
rows.append(summarise(f"Model at threshold {threshold:.2f}", prob >= threshold))
for pct in (10, 20):
    rows.append(summarise(f"Model, top {pct}%", top_k(int(n * pct / 100))))
    rows.append(summarise(f"Random, top {pct}% (expected)",
                          np.zeros(n, dtype=bool)) | {
        "customers_flagged": int(n * pct / 100), "share_contacted_pct": pct,
        "churners_caught": round(churners * pct / 100, 1),
        "precision_pct": round(100 * churners / n, 1),
        "churners_captured_pct": pct, "auto_renew_churners_caught": "-"})

out = pd.DataFrame(rows)
out["test_customers"], out["test_churners"] = n, churners
out["source_script"] = "24_benchmark_rules.py"
out.to_csv(OUTPUT_FILE, index=False)

pd.set_option("display.width", 200, "display.max_columns", 20)
print(f"Test customers: {n:,}  churners: {churners}  "
      f"manual-renew: {manual.sum()}  auto-renew: {auto.sum()}  "
      f"lapsed 31+: {lapsed.sum()}")
print(out.drop(columns=["test_customers", "test_churners",
                        "source_script"]).to_string(index=False))
print(f"\nSaved: {OUTPUT_FILE.name}")
