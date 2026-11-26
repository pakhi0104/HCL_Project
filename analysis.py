"""
analysis.py
The calculations behind the dashboard (totals, change, forecast).
No Streamlit and no database here, so it is easy to test.
"""

import calendar
from datetime import datetime

import pandas as pd

from clean_data import get_limit_for_month

COLUMNS = ["date", "description", "amount", "category", "month"]


def to_dataframe(rows):
    """Turn the list of rows from the database into a table (DataFrame)."""
    if not rows:
        return pd.DataFrame(columns=COLUMNS)
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["expense_date"])
    df["amount"] = df["amount"].astype(float)
    df["month"] = df["date"].dt.strftime("%Y-%m")
    return df[COLUMNS]


def month_label(month):
    """'2026-09' -> 'Sep 2026'."""
    return datetime.strptime(month, "%Y-%m").strftime("%b %Y")


def monthly_totals(df):
    """Net spend per month (refunds subtracted). Columns: month, total."""
    totals = df.groupby("month", as_index=False)["amount"].sum()
    return totals.rename(columns={"amount": "total"}).sort_values("month")


def category_totals(df):
    """Net spend per category, biggest first. Columns: category, total."""
    totals = df.groupby("category", as_index=False)["amount"].sum()
    return totals.rename(columns={"amount": "total"}).sort_values("total", ascending=False)


def change_vs_previous(df, month):
    """Percent change of a month compared with the previous calendar month.
    Returns None if there is no previous month or it was zero."""
    year, mon = int(month[:4]), int(month[5:7])
    prev = f"{year - 1}-12" if mon == 1 else f"{year}-{mon - 1:02d}"
    totals = dict(zip(*[monthly_totals(df)[c] for c in ("month", "total")]))
    if month not in totals or prev not in totals or totals[prev] == 0:
        return None
    return 100 * (totals[month] - totals[prev]) / totals[prev]


def forecast(df, limits, today, use_latest_if_none=False):
    """Predict the month-end total of the current month.

    forecast = (spent so far / days passed) * days in month

    If the current month has no expenses and use_latest_if_none is True
    (used for the sample demo), the latest month in the data is used,
    counted up to its last expense date.
    Returns a dictionary, or None if no forecast is possible.
    """
    if df.empty:
        return None

    month = today.strftime("%Y-%m")
    as_of = today
    is_fallback = False

    if df[df["month"] == month].empty:
        if not use_latest_if_none:
            return None
        month = df["month"].max()
        as_of = df[df["month"] == month]["date"].max().date()
        is_fallback = True

    month_df = df[(df["month"] == month) & (df["date"].dt.date <= as_of)]
    spent = float(month_df["amount"].sum())
    days_passed = as_of.day
    days_in_month = calendar.monthrange(as_of.year, as_of.month)[1]
    projected = spent / days_passed * days_in_month

    limit = get_limit_for_month(month, limits)
    gap = None if limit is None else projected - limit

    return {
        "month": month,
        "as_of": as_of,
        "spent": spent,
        "projected": projected,
        "limit": limit,
        "gap": gap,
        "days_passed": days_passed,
        "days_in_month": days_in_month,
        "is_fallback": is_fallback,
    }


def daily_cumulative(df, month, as_of):
    """Running total of the net spend of a month, day by day, up to as_of.
    Columns: day, cumulative."""
    month_df = df[(df["month"] == month) & (df["date"].dt.date <= as_of)]
    per_day = month_df.groupby(month_df["date"].dt.day)["amount"].sum()
    days = list(range(1, as_of.day + 1))
    cumulative = per_day.reindex(days, fill_value=0).cumsum()
    return pd.DataFrame({"day": days, "cumulative": cumulative.values})


def category_by_month(df):
    """Net spend per month and category. Columns: month, category, amount."""
    out = df.groupby(["month", "category"], as_index=False)["amount"].sum()
    return out.sort_values(["month", "category"])