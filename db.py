"""
db.py
All the code that talks to Supabase. The dashboard imports these functions.

Needs a .env file (in the same folder) containing:
    SUPABASE_URL=...
    SUPABASE_KEY=...
When deployed on Streamlit Community Cloud, the same two names are put in the
app's Secrets instead.
"""

import os

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()          
_client = None        

def _setting(name):
    """Read a setting from the .env file / environment, or from Streamlit's
    secrets (used when the app is deployed on Streamlit Community Cloud)."""
    value = os.getenv(name)
    if value:
        return value
    try:
        import streamlit as st
        return st.secrets.get(name)
    except Exception:
        return None
    
def get_client():
    """Return the Supabase connection (created the first time it is needed)."""
    global _client
    if _client is None:
        url = _setting("SUPABASE_URL")
        key = _setting("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL or SUPABASE_KEY is missing. "
                               "Check your .env file (or the app's Secrets when deployed).")
        _client = create_client(url, key)
    return _client

def login(name):
    """Find the user by name, or create a new one.
    Returns (profile, None) if OK, or (None, 'error message')."""
    display_name = " ".join(str(name).split())       # trim extra spaces
    user_name = display_name.lower()                 # 'Riya' and 'riya' are the same user

    if user_name == "":
        return None, "Please enter your name"
    if len(user_name) > 30:
        return None, "Name is too long (30 letters maximum)"
    if user_name == "sample":
        return None, "This name is reserved. Please use another name"

    client = get_client()
    found = client.table("profiles").select("*").eq("user_name", user_name).execute().data
    if found:
        return found[0], None

    client.table("profiles").insert({
        "user_name": user_name,
        "display_name": display_name,
        "show_sample": True,
    }).execute()
    return {"user_name": user_name, "display_name": display_name, "show_sample": True}, None

def set_show_sample(user_name, show):
    """True = show the sample demo. False = the user uses their own data."""
    get_client().table("profiles").update({"show_sample": show}).eq("user_name", user_name).execute()

def get_expenses(owner):
    """All expenses of one owner ('sample' or a user name), oldest first."""
    client = get_client()
    rows = []
    start = 0
    page_size = 1000                                  # fetch 1000 rows at a time
    while True:
        chunk = (client.table("expenses")
                 .select("expense_date,description,amount,category")
                 .eq("owner", owner)
                 .order("expense_date")
                 .order("expense_id")
                 .range(start, start + page_size - 1)
                 .execute().data)
        rows.extend(chunk)
        if len(chunk) < page_size:
            break
        start += page_size
    return rows

def get_limits(owner):
    """Monthly limits of one owner as a dictionary, like {'2026-06': 18000.0}."""
    data = (get_client().table("budget")
            .select("month,limit_amount")
            .eq("owner", owner)
            .execute().data)
    return {r["month"]: float(r["limit_amount"]) for r in data}

def get_budget_check(owner, month=None):
    """Run the PL/pgSQL function check_budget() for one owner.
    Returns a list of rows: budget_month, spent, month_limit, over_by, status."""
    params = {"p_owner": owner}
    if month:
        params["p_month"] = month
    return get_client().rpc("check_budget", params).execute().data

def expense_exists(owner, row):
    """True if this owner already has the same date + description + amount.
    row is the clean row returned by clean_expense()."""
    found = (get_client().table("expenses")
             .select("expense_id")
             .eq("owner", owner)
             .eq("expense_date", row["date"])
             .eq("description", row["description"])
             .eq("amount", row["amount"])
             .limit(1)
             .execute().data)
    return len(found) > 0

def save_expense(owner, row):
    """Save one clean expense (the row returned by clean_expense())."""
    get_client().table("expenses").insert({
        "owner": owner,
        "expense_date": row["date"],
        "description": row["description"],
        "amount": row["amount"],
        "category": row["category"],
    }).execute()

def save_limit(owner, month, limit):
    """Save the limit of a month. If the month already has one, it is replaced."""
    get_client().table("budget").upsert(
        {"owner": owner, "month": month, "limit_amount": limit},
        on_conflict="owner,month",
    ).execute()