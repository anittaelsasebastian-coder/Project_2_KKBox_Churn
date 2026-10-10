from pathlib import Path
import pandas as pd
from statsmodels.stats.multitest import multipletests

BASE_DIR = Path(__file__).resolve().parent

files = {
    "Categorical": BASE_DIR / "statistical_categorical_results.csv",
    "Numeric": BASE_DIR / "statistical_numeric_results.csv",
}

for name, path in files.items():
    print(f"\n{'=' * 65}")
    print(f"{name.upper()} STATISTICAL RESULTS REVIEW")
    print("=" * 65)

    df = pd.read_csv(path)

    if "p_value" not in df.columns:
        print("Expected column 'p_value' not found.")
        print("Available columns:", df.columns.tolist())
        continue

    df["p_value"] = pd.to_numeric(df["p_value"], errors="coerce")
    valid = df["p_value"].notna()

    df["adjusted_p_value"] = float("nan")

    if valid.any():
        df.loc[valid, "adjusted_p_value"] = multipletests(
            df.loc[valid, "p_value"],
            method="fdr_bh"
        )[1]

    print("Columns:", df.columns.tolist())
    print("\nResults sorted by adjusted p-value:")
    print(
        df.sort_values("adjusted_p_value")
        .to_string(index=False)
    )

    output_path = BASE_DIR / (
        "reviewed_" + path.name
    )
    df.to_csv(output_path, index=False)
    print(f"\nSaved reviewed results: {output_path.name}")

print("\nSTATISTICAL REVIEW COMPLETE")