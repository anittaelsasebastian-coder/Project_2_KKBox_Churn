import pandas as pd

old = pd.read_csv("logistic_before_tiebreak.csv").set_index("term")
new = pd.read_csv("logistic_regression_results.csv").set_index("term")

cols = ["odds_ratio", "p_adjusted_bh", "significant_after_bh_0_05"]
both = old[cols].join(new[cols], lsuffix="_old", rsuffix="_new")

pd.set_option("display.width", 200)
print(both.round(4).to_string())

flipped = both[
    both["significant_after_bh_0_05_old"] != both["significant_after_bh_0_05_new"]
]
print()
print("Terms whose significance changed:", len(flipped))

print()
old_m = pd.read_csv("metrics_before_tiebreak.csv").iloc[0]
new_m = pd.read_csv("churn_model_evaluation_metrics.csv").iloc[0]
for k in ["roc_auc", "pr_auc_average_precision", "precision", "recall"]:
    print(k, "old:", round(float(old_m[k]), 4), "new:", round(float(new_m[k]), 4))