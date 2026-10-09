import pandas as pd

# Load the SQL analysis export
file_path = "Project_2_KKBox_Churn_Analysis.csv"

df = pd.read_csv(file_path)

print("Rows:", len(df))
print("Columns:", len(df.columns))

print("\nChurn distribution:")
print(df["is_churn"].value_counts())

print("\nChurn rate:")
print(df["is_churn"].mean())

print("\nFirst 5 rows:")
print(df.head())
print("\n" + "=" * 50)
print("DATA QUALITY CHECK")
print("=" * 50)

# 1. Duplicate customers
print("\nDuplicate customers:")
print(df["msno"].duplicated().sum())

# 2. Missing values
print("\nMissing values:")
print(df.isna().sum())

# 3. Age range
print("\nAge range:")
print("Minimum age:", df["bd"].min())
print("Maximum age:", df["bd"].max())

# 5. Risk segment
print("\nRisk segment:")
print(df["risk_segment"].value_counts(dropna=False))

# 5. Risk segment
print("\nRisk segment:")
print(df["risk_segment"].value_counts(dropna=False))
# Transaction history based on latest transaction date
transaction_status = df["latest_transaction_date"].isna().map({
    True: "No transaction history",
    False: "Has transaction history"
})

print("\nTransaction history:")
print(transaction_status.value_counts())

# Usage history based on last active date
usage_status = df["last_active_date"].isna().map({
    True: "No usage history",
    False: "Has usage history"
})

print("\nUsage history:")
print(usage_status.value_counts())