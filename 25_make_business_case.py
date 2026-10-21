"""Build business_case.xlsx: costed scenarios, break-even and pilot sample size.

Every number a reader might change is an input cell (blue text). Yellow cells
are assumptions. All results are live Excel formulas.
"""
from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

OUT = "business_case.xlsx"
F = "Arial"
BLUE, BOLD, NORM = Font(name=F, color="0000FF"), Font(name=F, bold=True), Font(name=F)
TITLE, NOTE = Font(name=F, bold=True, size=14), Font(name=F, italic=True, color="555555")
YELLOW = PatternFill("solid", fgColor="FFFF00")
HEAD = PatternFill("solid", fgColor="D9E1F2")
THIN = Border(bottom=Side(style="thin", color="999999"))
NTD, PCT, INT = '#,##0;(#,##0);"-"', '0.0%;(0.0%);"-"', '#,##0'

wb = Workbook()


def cell(ws, ref, value, font=NORM, fmt=None, fill=None, note=None):
    c = ws[ref]; c.value = value; c.font = font
    if fmt: c.number_format = fmt
    if fill: c.fill = fill
    if note: c.comment = Comment(note, "Analyst")
    return c


def header(ws, row, labels):
    for i, lab in enumerate(labels):
        c = ws.cell(row=row, column=i + 1, value=lab)
        c.font, c.fill, c.border = BOLD, HEAD, THIN


# ---------------- Inputs ----------------
ws = wb.active; ws.title = "Inputs"
cell(ws, "A1", "KKBox auto-renew nudge pilot: business case", TITLE)
cell(ws, "A2", "Blue text = input you can change. Yellow fill = assumption, not data. "
     "All other numbers are formulas.", NOTE)
header(ws, 4, ["Input", "Value", "Source"])
rows = [
    ("Manual-renew customers in sample", 1015, INT, None,
     "dashboard_outputs/renewal_summary.csv"),
    ("Baseline churn, manual-renew", 0.4158, PCT, None,
     "dashboard_outputs/renewal_summary.csv"),
    ("Avg monthly revenue of a churned manual-renew customer (NTD)", 140.76, NTD,
     None, "dashboard_outputs/scenario_summary.csv"),
]
for i, (lab, val, fmt, fill, src) in enumerate(rows, start=5):
    cell(ws, f"A{i}", lab); cell(ws, f"B{i}", val, BLUE, fmt, fill); cell(ws, f"C{i}", src)
cell(ws, "A9", "Scenario levers are on the Scenarios sheet (row 5 to 10).", NOTE)
ws.column_dimensions["A"].width = 62; ws.column_dimensions["B"].width = 14
ws.column_dimensions["C"].width = 44

# ---------------- Scenarios ----------------
sc = wb.create_sheet("Scenarios")
cell(sc, "A1", "Costed scenarios (sample scale: customers contacted = manual-renew sample)", TITLE)
cell(sc, "A2", "Levers in yellow are assumptions. Change them to test the case.", NOTE)
header(sc, 4, ["Lever (assumption)", "Low", "Base", "High"])
levers = [
    ("Churn reduction (percentage points)", (0.02, 0.05, 0.10), PCT,
     "Planning values, not estimates. The pilot measures the real effect."),
    ("Months a saved customer stays", (3, 6, 12), INT, "Assumption."),
    ("Contribution margin on revenue", (0.25, 0.30, 0.35), PCT,
     "Assumption. Music streaming margins are thin after royalties."),
    ("Contact cost per customer (NTD)", (5, 2, 1), NTD, "Assumption: email and in-app prompt."),
    ("Opt-in rate to auto-renew", (0.20, 0.30, 0.40), PCT, "Assumption."),
    ("Incentive per opt-in (NTD)", (30, 0, 0), NTD,
     "Base design has no price incentive. Low case tests a 30 NTD incentive."),
]
for r, (lab, vals, fmt, note) in enumerate(levers, start=5):
    cell(sc, f"A{r}", lab, note=note)
    for col, v in zip("BCD", vals):
        cell(sc, f"{col}{r}", v, BLUE, fmt, YELLOW)

header(sc, 12, ["Result (formula)", "Low", "Base", "High"])
results = [
    ("Customers contacted", "=Inputs!$B$5", INT),
    ("Avoided churners", "={c}13*{c}5", '#,##0.0'),
    ("Retained contribution (NTD)", "={c}14*Inputs!$B$7*{c}7*{c}6", NTD),
    ("Programme cost (NTD)", "={c}13*{c}8+{c}13*{c}9*{c}10", NTD),
    ("Net value (NTD)", "={c}15-{c}16", NTD),
    ("Return on cost", '=IFERROR({c}17/{c}16,"n/a")', '0.0x'),
    ("Break-even churn reduction (points)",
     '=IFERROR({c}16/({c}13*Inputs!$B$7*{c}7*{c}6),0)', PCT),
    ("Assumed effect vs break-even",
     '=IF({c}5>={c}19,"Above break-even","Below break-even")', None),
]
for r, (lab, f, fmt) in enumerate(results, start=13):
    cell(sc, f"A{r}", lab, BOLD if r in (17, 19) else NORM)
    for col in "BCD":
        cell(sc, f"{col}{r}", f.format(c=col), BOLD if r in (17, 19) else NORM, fmt)

cell(sc, "A22", "Sensitivity: net value (NTD) by churn reduction, other levers at Base", BOLD)
header(sc, 23, ["Churn reduction (points)", "Net value (NTD)"])
for r, eff in enumerate((0.01, 0.02, 0.03, 0.05, 0.07, 0.10), start=24):
    cell(sc, f"A{r}", eff, BLUE, PCT)
    cell(sc, f"B{r}", f"=$C$13*A{r}*Inputs!$B$7*$C$7*$C$6-$C$16", NORM, NTD)
cell(sc, "A31", "Sample scale only. At full scale, multiply customers contacted by "
     "the eligible volume. Figures are what-ifs, not forecasts.", NOTE)
sc.column_dimensions["A"].width = 44
for col in "BCD": sc.column_dimensions[col].width = 16

# ---------------- Pilot sample size ----------------
ps = wb.create_sheet("Pilot")
cell(ps, "A1", "Pilot sample size (two-proportion test, 1:1 randomisation)", TITLE)
header(ps, 3, ["Input", "Value"])
cell(ps, "A4", "Baseline churn (from Inputs)"); cell(ps, "B4", "=Inputs!B6", NORM, PCT)
cell(ps, "A5", "Minimum effect to detect (points)")
cell(ps, "B5", 0.05, BLUE, PCT, YELLOW, "Planning assumption.")
cell(ps, "A6", "Significance (two-sided)"); cell(ps, "B6", 0.05, BLUE, PCT)
cell(ps, "A7", "Power"); cell(ps, "B7", 0.80, BLUE, PCT)
header(ps, 9, ["Result (formula)", "Value"])
cell(ps, "A10", "Customers per arm", BOLD)
cell(ps, "B10", "=ROUNDUP((NORMSINV(1-B6/2)+NORMSINV(B7))^2*(B4*(1-B4)+(B4-B5)*(1-(B4-B5)))/B5^2,0)",
     BOLD, INT)
cell(ps, "A11", "Total eligible customers needed"); cell(ps, "B11", "=2*B10", NORM, INT)
cell(ps, "A13", "Monthly eligible volume at full scale")
cell(ps, "B13", None, BLUE, INT, YELLOW,
     "Unknown outside the sample. Confirm with Retention, then type it here.")
cell(ps, "A14", "Months of enrolment needed")
cell(ps, "B14", '=IF(B13="","Enter volume in B13",ROUNDUP(B11/B13,0))', NORM, INT)
cell(ps, "A16", "The 7,500-customer analysis sample is not the pilot population. "
     "The pilot runs on the full customer base, so feasibility depends on B13.", NOTE)
ps.column_dimensions["A"].width = 44; ps.column_dimensions["B"].width = 18

# ---------------- Assumption log ----------------
al = wb.create_sheet("Assumption log")
header(al, 1, ["Item", "Type", "Where", "Why it matters"])
log = [
    ("Churn reduction 2 / 5 / 10 points", "Assumption", "Scenarios row 5", "Drives all value"),
    ("Months retained 3 / 6 / 12", "Assumption", "Scenarios row 6", "Scales value linearly"),
    ("Margin 25% / 30% / 35%", "Assumption", "Scenarios row 7", "Revenue is not profit"),
    ("Contact cost 5 / 2 / 1 NTD", "Assumption", "Scenarios row 8", "Main programme cost"),
    ("Opt-in rate, incentive", "Assumption", "Scenarios rows 9-10", "Only matters with an incentive"),
    ("5-point minimum effect", "Assumption", "Pilot B5", "Smaller effect needs a bigger pilot"),
    ("Monthly eligible volume", "Unknown", "Pilot B13", "Decides pilot duration"),
    ("Customers, churn, revenue", "Data (sample)", "Inputs B5:B7", "2017 sample, not company-wide"),
]
for r, row in enumerate(log, start=2):
    for c, v in enumerate(row, start=1):
        al.cell(row=r, column=c, value=v).font = NORM
for col, w in zip("ABCD", (36, 16, 22, 36)): al.column_dimensions[col].width = w

for sheet in wb.worksheets:
    for row in sheet.iter_rows():
        for c in row:
            c.alignment = Alignment(vertical="center")
wb.save(OUT)
print(f"Saved: {OUT}")
