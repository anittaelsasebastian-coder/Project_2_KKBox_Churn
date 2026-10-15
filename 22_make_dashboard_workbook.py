from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
IN_DIR = BASE_DIR / "dashboard_outputs"
OUT_FILE = IN_DIR / "kkbox_dashboard_data.xlsx"

TABLES = [
    "overall_kpis", "renewal_summary", "recency_summary",
    "engagement_summary", "scenario_summary", "model_metrics",
    "confusion_matrix", "lift_by_decile",
]

with pd.ExcelWriter(OUT_FILE, engine="openpyxl") as writer:
    for name in TABLES:
        table = pd.read_csv(IN_DIR / f"{name}.csv")
        assert "msno" not in table.columns, f"Customer IDs found in {name}"
        if name == "scenario_summary":
            table["currency"] = "NTD"
        table.to_excel(writer, sheet_name=name, index=False)
        print(f"Added sheet {name}: {len(table)} rows")

print(f"\nSaved: {OUT_FILE.name}")