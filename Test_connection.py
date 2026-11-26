"""
test_connection.py
Checks that Python can talk to Supabase and that the SQL files were run correctly.

Run:  python test_connection.py
"""

from db import get_client, get_expenses, get_limits, get_budget_check

try:
    print("Connecting to Supabase...")
    client = get_client()

    categories = client.table("category").select("category_name").execute().data
    print("Categories found:", len(categories), "(expected 9)")

    expenses = get_expenses("sample")
    print("Sample expenses: ", len(expenses), "(expected 109)")

    print("Sample limits:   ", get_limits("sample"))

    print("Budget check (PL/pgSQL):")
    for r in get_budget_check("sample"):
        print("  ", r["budget_month"], r["spent"], r["month_limit"], r["status"])

    print("Connection works.")

except Exception as error:
    print("Something went wrong:")
    print(error)
    print("Check: .env values, internet, and that all SQL files were run in order.")