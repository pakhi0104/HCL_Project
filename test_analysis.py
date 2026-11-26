"""
test_analysis.py
Checks the dashboard calculations without Streamlit or the database.

Run:  python test_analysis.py
"""

import csv
from datetime import date

from analysis import (to_dataframe, monthly_totals, category_totals,
                      change_vs_previous, forecast, month_label,
                      daily_cumulative, category_by_month)

# Load the clean sample data from the CSV
with open("expenses_clean.csv", newline="", encoding="utf-8") as f:
    rows = [{"expense_date": r["date"], "description": r["description"],
             "amount": r["amount"], "category": r["category"]}
            for r in csv.DictReader(f)]

df = to_dataframe(rows)
limits = {m: 18000.0 for m in ["2026-06", "2026-07", "2026-08", "2026-09", "2026-10", "2026-11"]}

# Monthly totals match the data-quality report
totals = dict(zip(monthly_totals(df)["month"], monthly_totals(df)["total"]))
assert round(totals["2026-06"]) == 16688
assert round(totals["2026-09"]) == 22838
assert round(totals["2026-11"]) == 17578

# Category totals add up to the grand total
assert round(category_totals(df)["total"].sum(), 2) == round(df["amount"].sum(), 2)

# Change vs previous month: Sep vs Aug
assert round(change_vs_previous(df, "2026-09"), 1) == round(100 * (22838 - 16888) / 16888, 1)
assert change_vs_previous(df, "2026-06") is None          # no May data

# Forecast on 26 Nov 2026: 17578 / 26 * 30
fc = forecast(df, limits, date(2026, 11, 26))
assert fc["month"] == "2026-11" and not fc["is_fallback"]
assert round(fc["projected"]) == round(17578 / 26 * 30)
assert fc["gap"] > 0                                        # overshoot of the 18000 limit

# Forecast when today is in a month without data
assert forecast(df, limits, date(2027, 3, 10)) is None
fallback = forecast(df, limits, date(2027, 3, 10), use_latest_if_none=True)
assert fallback["is_fallback"] and fallback["month"] == "2026-11"
assert fallback["as_of"] == date(2026, 11, 25)

# Empty data
assert forecast(to_dataframe([]), limits, date(2026, 11, 26)) is None

# Daily running total for the forecast graph
daily = daily_cumulative(df, "2026-11", date(2026, 11, 26))
assert len(daily) == 26 and daily["day"].iloc[0] == 1 and daily["day"].iloc[-1] == 26
assert round(daily["cumulative"].iloc[-1]) == 17578
assert (daily["cumulative"].diff().dropna() != 0).any()

# Category by month adds up to the grand total
assert round(category_by_month(df)["amount"].sum(), 2) == round(df["amount"].sum(), 2)

# Month label
assert month_label("2026-09") == "Sep 2026"

print("All dashboard calculation tests passed.")
print("Forecast for Nov 2026 (as of 26 Nov): Rs", round(fc["projected"]),
      "| over limit by Rs", round(fc["gap"]))