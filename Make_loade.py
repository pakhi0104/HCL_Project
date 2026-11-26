"""
make_load_sql.py
Reads expenses_clean.csv and budget.csv and writes 02_load.sql
(INSERT statements you paste into the Supabase SQL Editor).
All rows are loaded with owner = 'sample' (the demo data).

Run:  python make_load_sql.py
Run it again whenever you regenerate or re-clean the data.
"""

import csv

OWNER = "sample"


def sql_text(value):
    """Wrap text in quotes for SQL and double any single quote inside it."""
    return "'" + str(value).replace("'", "''") + "'"


lines = ["-- 02_load.sql", "-- Loads the SAMPLE (demo) budget limits and expenses.",
         "-- Run 01_ddl.sql first.", ""]

# ----- budget table -----
with open("budget.csv", newline="", encoding="utf-8") as f:
    budget_rows = list(csv.DictReader(f))

lines.append("insert into budget (owner, month, limit_amount) values")
values = [f"    ({sql_text(OWNER)}, {sql_text(r['month'])}, {float(r['limit_amount']):.2f})"
          for r in budget_rows]
lines.append(",\n".join(values) + ";")
lines.append("")

with open("expenses_clean.csv", newline="", encoding="utf-8") as f:
    expense_rows = list(csv.DictReader(f))

lines.append("insert into expenses (owner, expense_date, description, amount, category) values")
values = [
    f"    ({sql_text(OWNER)}, {sql_text(r['date'])}, {sql_text(r['description'])}, "
    f"{float(r['amount']):.2f}, {sql_text(r['category'])})"
    for r in expense_rows
]
lines.append(",\n".join(values) + ";")
lines.append("")

lines.append("-- Check: these monthly totals must match data_quality_report.txt")
lines.append("select to_char(expense_date, 'YYYY-MM') as month, sum(amount) as total")
lines.append("from expenses")
lines.append(f"where owner = {sql_text(OWNER)}")
lines.append("group by 1")
lines.append("order by 1;")

with open("02_load.sql", "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

print("Done. 02_load.sql created with", len(budget_rows), "budget rows and",
      len(expense_rows), "expense rows.")