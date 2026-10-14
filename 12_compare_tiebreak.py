import pandas as pd

old = pd.read_csv("model_dataset_before_tiebreak.csv").set_index("msno").sort_index()
new = pd.read_csv("kkbox_leakage_safe_model_dataset.csv").set_index("msno").sort_index()

print("Same customers:", old.index.equals(new.index))
print("Same columns:", list(old.columns) == list(new.columns))

changed_cols = {}
affected = set()
for col in old.columns:
    diff = ~((old[col] == new[col]) | (old[col].isna() & new[col].isna()))
    if diff.any():
        changed_cols[col] = int(diff.sum())
        affected.update(old.index[diff])

print("Customers with any changed value:", len(affected))
print("Columns that changed (and how many customers):")
for col, n in changed_cols.items():
    print(f"  {col}: {n}")