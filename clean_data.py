"""
clean_data.py
Reads expenses_raw.csv, cleans + categorises every row using cleaning.py,
and writes:
  expenses_clean.csv     - clean rows
  rejected_rows.csv      - rows that failed validation, with the reason
  data_quality_report.txt - counts for your data-quality report

Run:  python clean_data.py
"""
import csv
from collections import Counter
from cleaning import clean_entry, UNCATEGORISED

RAW_FILE = "expenses_raw.csv"
CLEAN_FILE = "expenses_clean.csv"
REJECT_FILE = "rejected_rows.csv"
REPORT_FILE = "data_quality_report.txt"

with open(RAW_FILE, newline="", encoding="utf-8") as f:
    raw_rows = list(csv.DictReader(f))

clean_rows, rejected = [], []
for row in raw_rows:
    record, error = clean_entry(row["date"], row["description"], row["amount"])
    if error:
        rejected.append({**row, "reason": error})
    else:
        clean_rows.append(record)

seen, unique_rows, duplicates = set(), [], 0
for r in clean_rows:
    key = (r["date"], r["description"], r["amount"])
    if key in seen:
        duplicates += 1
        continue
    seen.add(key)
    unique_rows.append(r)

unique_rows.sort(key=lambda r: r["date"])
fields = ["date", "description", "amount", "category", "is_refund", "year_month"]
with open(CLEAN_FILE, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(unique_rows)
with open(REJECT_FILE, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["date", "description", "amount", "reason"])
    w.writeheader()
    w.writerows(rejected)
total = len(unique_rows)
uncat = sum(1 for r in unique_rows if r["category"] == UNCATEGORISED)
rate = (total - uncat) / total * 100 if total else 0
refunds = sum(1 for r in unique_rows if r["is_refund"])
by_month = Counter()
for r in unique_rows:
    by_month[r["year_month"]] += r["amount"]

lines = [
    f"Raw rows read:            {len(raw_rows)}",
    f"Rejected (invalid):       {len(rejected)}",
    f"Duplicates removed:       {duplicates}",
    f"Clean rows kept:          {total}",
    f"Refund rows:              {refunds}",
    f"Uncategorised rows:       {uncat}",
    f"Categorisation rate:      {rate:.1f}%  (target: 90%+)",
    "",
    "Monthly totals (clean data):",
] + [f"  {m}: {by_month[m]:,.2f}" for m in sorted(by_month)]

report = "\n".join(lines)
print(report)
with open(REPORT_FILE, "w", encoding="utf-8") as f:
    f.write(report + "\n")