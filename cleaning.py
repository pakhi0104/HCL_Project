"""
cleaning.py
Reusable cleaning + categorisation functions.

Used by BOTH:
  - clean_data.py          (batch: every row of expenses_raw.csv)
  - the Streamlit form     (one new entry at a time)
so sample data and typed data follow exactly the same rules.
"""
import re
import math
from datetime import date, datetime
CATEGORY_KEYWORDS = {
    "Food":          ["swiggy", "zomato", "dominos", "starbucks"],
    "Groceries":     ["bigbasket", "blinkit"],
    "Transport":     ["uber", "ola", "metro recharge", "petrol pump"],
    "Shopping":      ["amazon", "flipkart", "myntra"],
    "Bills":         ["house rent", "electricity bill", "jio"],
    "Entertainment": ["netflix", "bookmyshow"],
    "Health":        ["apollo pharmacy"],
    "Education":     ["udemy"],
}
UNCATEGORISED = "Uncategorised"

DATE_FORMATS = ["%Y-%m-%d", "%d %b %Y"]     # 2026-08-12  and  12 Aug 2026

def categorise(description):
    """Return the category for a description, or 'Uncategorised'.

    Matches whole words/phrases, ignoring case, so
    'Amazon Refund' -> Shopping, but 'Cola Shop' does NOT match 'ola'.
    """
    text = str(description).lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", text):
                return category
    return UNCATEGORISED

def _parse_date(value):
    """Accept a date/datetime object or a text date in a known format."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None

def _parse_amount(value):
    """Return a float, or None if blank / not a number / NaN."""
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if text == "":
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number

def clean_entry(raw_date, description, amount, max_date=None):
    """Clean ONE expense.

    Returns (record, error):
      - valid entry   -> (dict, None)
      - invalid entry -> (None, "reason text")

    max_date: optional date; entries after it are rejected
              (the form can pass date.today()).
    """

    if description is None or str(description).strip() == "":
        return None, "Description is empty"
    clean_desc = " ".join(str(description).split()).title()

    amt = _parse_amount(amount)
    if amt is None:
        return None, "Amount is missing or not a number"
    if amt == 0:
        return None, "Amount cannot be zero"

    d = _parse_date(raw_date)
    if d is None:
        return None, f"Date '{raw_date}' not recognised"
    if max_date is not None and d > max_date:
        return None, "Date is in the future"

    record = {
        "date": d.isoformat(),
        "description": clean_desc,
        "amount": round(amt, 2),
        "category": categorise(clean_desc),
        "is_refund": amt < 0,
        "year_month": d.strftime("%Y-%m"),
    }
    return record, None

def is_duplicate(record, existing_records):
    """True if same date + description + amount already exists.

    existing_records: iterable of dicts (or rows) with those 3 keys.
    The CSV script drops these silently; the form can just warn.
    """
    key = (record["date"], record["description"], record["amount"])
    return any(
        (str(r["date"]), r["description"], float(r["amount"])) == key
        for r in existing_records
    )