"""
clean_data.py
Cleans and categorises expenses.

Used in two places:
  1. For the sample data:   python clean_data.py
        reads expenses_raw.csv, writes expenses_clean.csv and data_quality_report.txt
  2. For every expense typed in the dashboard form:
        the form calls clean_expense() and is_duplicate() from this file.

To run the 3 test cases:   python clean_data.py test
"""

import csv
import sys
from datetime import date, datetime

CATEGORY_KEYWORDS = {
    "Food": ["swiggy", "zomato", "dominos", "starbucks", "bigbasket", "blinkit"],
    "Travel": ["uber", "ola", "metro", "petrol"],
    "Shopping": ["amazon", "flipkart", "myntra"],
    "Rent": ["rent"],
    "Entertainment": ["netflix", "bookmyshow"],
    "Bills": ["jio", "electricity"],
    "Health": ["apollo"],
    "Education": ["udemy"],
}

DATE_FORMATS = ["%Y-%m-%d", "%d %b %Y", "%d/%m/%Y", "%d-%m-%Y"]

def clean_description(text):
    """Remove extra spaces and fix capital letters: '  SWIGGY ' -> 'Swiggy'."""
    return " ".join(str(text).split()).title()

def clean_date(value):
    """Convert a date into 'YYYY-MM-DD'. Returns None if it cannot be read."""
    if isinstance(value, datetime):          
        return value.date().isoformat()
    if isinstance(value, date):             
        return value.isoformat()
    text = str(value).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass                             
    return None

def clean_amount(value):
    """Convert an amount to a number. Returns None if missing or not valid.
    Negative amounts are kept: they are refunds."""
    text = str(value).replace(",", "").replace("\u20b9", "").strip()
    try:
        amount = float(text)
    except ValueError:
        return None
    if amount != amount or amount == 0 or abs(amount) > 10_000_000:
        return None                          
    return round(amount, 2)

def categorise(description):
    """Return the category of a description, or 'Uncategorised'."""
    words = description.lower().split()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in words:
                return category
    return "Uncategorised"

def clean_limit(value):
    """Convert a monthly limit to a number.
    Returns None if it is empty, text, zero, negative, or silly big."""
    text = str(value).replace(",", "").replace("\u20b9", "").strip()
    try:
        limit = float(text)
    except ValueError:
        return None
    if limit != limit or limit <= 0 or limit > 10_000_000:
        return None
    return round(limit, 2)

def get_limit_for_month(month, limits):
    """Find the limit to use for a month like '2026-12'.
    limits is a dictionary like {'2026-06': 18000.0, '2026-07': 18000.0}.
    - If the month has a limit, use it.
    - Otherwise copy the limit of the latest earlier month.
    - If there is no earlier month either, return None."""
    if month in limits:
        return limits[month]
    earlier = [m for m in limits if m < month]    
    if earlier:
        return limits[max(earlier)]
    return None

def clean_expense(raw_date, raw_description, raw_amount):
    """Clean ONE expense.
    Returns (row, None) if it is good, or (None, 'error message') if it is bad."""
    date_text = clean_date(raw_date)
    if date_text is None:
        return None, "Date is not valid"

    amount = clean_amount(raw_amount)
    if amount is None:
        return None, "Amount is missing or not a valid number"

    description = clean_description(raw_description)
    if description == "":
        return None, "Description is empty"

    row = {
        "date": date_text,
        "description": description,
        "amount": amount,
        "category": categorise(description),
    }
    return row, None

def make_key(row):
    """Three values that identify an expense."""
    return (row["date"], row["description"], row["amount"])

def is_duplicate(row, existing_keys):
    """True if the same date + description + amount already exists.
    existing_keys is a set of make_key(...) values of the saved rows."""
    return make_key(row) in existing_keys

def clean_csv(input_file="expenses_raw.csv",
              output_file="expenses_clean.csv",
              report_file="data_quality_report.txt"):
    clean_rows = []
    seen = set()               # keys of rows already kept
    rejected = {}              # error message -> how many rows
    raw_count = 0
    duplicates = 0
    text_fixed = 0
    dates_fixed = 0

    with open(input_file, newline="", encoding="utf-8") as f:
        for raw in csv.DictReader(f):
            raw_count += 1
            row, error = clean_expense(raw.get("date", ""),
                                       raw.get("description", ""),
                                       raw.get("amount", ""))
            if error:
                rejected[error] = rejected.get(error, 0) + 1
                continue

            if is_duplicate(row, seen):          # duplicates are dropped silently
                duplicates += 1
                continue
            seen.add(make_key(row))

            if raw["description"] != row["description"]:
                text_fixed += 1
            if raw["date"].strip() != row["date"]:
                dates_fixed += 1
            clean_rows.append(row)

    clean_rows.sort(key=lambda r: r["date"])

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "description", "amount", "category"])
        writer.writeheader()
        writer.writerows(clean_rows)

    #Data-quality report
    uncategorised = sum(1 for r in clean_rows if r["category"] == "Uncategorised")
    refunds = sum(1 for r in clean_rows if r["amount"] < 0)

    category_counts = {}
    monthly_totals = {}
    for r in clean_rows:
        category_counts[r["category"]] = category_counts.get(r["category"], 0) + 1
        month = r["date"][:7]
        monthly_totals[month] = monthly_totals.get(month, 0) + r["amount"]

    lines = ["DATA QUALITY REPORT", "=" * 40]
    lines.append(f"Rows in raw file:            {raw_count}")
    lines.append(f"Rows rejected (invalid):     {sum(rejected.values())}")
    for message, count in rejected.items():
        lines.append(f"   - {message}: {count}")
    lines.append(f"Duplicates removed:          {duplicates}")
    lines.append(f"Descriptions fixed:          {text_fixed}")
    lines.append(f"Dates converted:             {dates_fixed}")
    lines.append(f"Final clean rows:            {len(clean_rows)}")
    percent = 100 * uncategorised / len(clean_rows)
    lines.append(f"Uncategorised:               {uncategorised} ({percent:.1f}%)")
    lines.append(f"Refund entries:              {refunds}")
    lines.append("")
    lines.append("Rows per category:")
    for category, count in sorted(category_counts.items()):
        lines.append(f"   {category:<15} {count}")
    lines.append("")
    lines.append("Monthly totals (refunds subtracted):")
    for month, total in sorted(monthly_totals.items()):
        lines.append(f"   {month}   Rs {total:>10,.2f}")

    report = "\n".join(lines)
    print(report)
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report + "\n")

# ---------- Test cases ----------
def run_tests():
    row, error = clean_expense("2026-06-05", "Random Shop", "100")
    assert error is None and row["category"] == "Uncategorised"

    row, error = clean_expense("2026-06-06", "Amazon Refund", "-500")
    assert row["amount"] == -500 and row["category"] == "Shopping"

    jan, _ = clean_expense("31 Jan 2026", "Swiggy", "200")
    feb, _ = clean_expense("1 Feb 2026", "Swiggy", "200")
    assert jan["date"] == "2026-01-31" and feb["date"] == "2026-02-01"

    row, _ = clean_expense("2026-06-07", "  SWIGGY  ", "250")
    assert row["description"] == "Swiggy" and row["category"] == "Food"

    row, error = clean_expense("2026-06-08", "Zomato", "")
    assert row is None and error is not None
    row, error = clean_expense("not a date", "Zomato", "100")
    assert row is None and error is not None

    first, _ = clean_expense("2026-06-09", "Uber", "300")
    keys = {make_key(first)}
    same, _ = clean_expense("09/06/2026", " uber ", "300")
    different, _ = clean_expense("2026-06-09", "Uber", "350")
    assert is_duplicate(same, keys) and not is_duplicate(different, keys)

    assert clean_limit("18000") == 18000
    assert clean_limit("20,000") == 20000
    assert clean_limit("") is None
    assert clean_limit("0") is None
    assert clean_limit("-500") is None
    assert clean_limit("abc") is None

    limits = {"2026-10": 18000.0, "2026-11": 20000.0}
    assert get_limit_for_month("2026-11", limits) == 20000.0
    assert get_limit_for_month("2026-12", limits) == 20000.0
    assert get_limit_for_month("2026-05", limits) is None

    print("All tests passed.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        run_tests()
    else:
        clean_csv()