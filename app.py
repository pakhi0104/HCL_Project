"""
app.py
The Streamlit dashboard of the Personal Expense Tracker.

Run:  streamlit run app.py

Flow:
  1. Login screen (name only, no password)
  2. Dashboard shows the SAMPLE data, with a button "Remove sample data..."
  3. After that the dashboard shows the user's OWN data and an Add expense form
"""

import html
from datetime import date

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import db
from analysis import (category_by_month, category_totals, change_vs_previous,
                      daily_cumulative, forecast, month_label, monthly_totals,
                      to_dataframe)
from clean_data import clean_expense, clean_limit, get_limit_for_month

st.set_page_config(page_title="Expense Tracker", page_icon="💰", layout="wide")

PALETTE = ["#4c78d0", "#e8833a", "#2e9e5b", "#d64545", "#8e6bbf",
           "#c9a227", "#3aa6b9", "#d46a9e", "#7f8c8d"]

CSS = """
<style>
.block-container { padding-top: 2rem; }
.card {
    border-radius: 14px; padding: 16px 18px; height: 100%;
    border: 1px solid rgba(128,128,128,.25);
    background: rgba(128,128,128,.07);
}
.card .t { font-size: .85rem; opacity: .75; }
.card .v { font-size: 1.8rem; font-weight: 700; line-height: 1.25; }
.card .s { font-size: .8rem; opacity: .75; }
.card.ok      { border-left: 6px solid #2e9e5b; }
.card.bad     { border-left: 6px solid #d64545; }
.card.neutral { border-left: 6px solid #4c78d0; }
.banner {
    border-radius: 12px; padding: 12px 16px; margin-bottom: 8px;
    background: rgba(76,120,208,.12); border: 1px solid rgba(76,120,208,.35);
}
.alert-bad {
    border-radius: 12px; padding: 10px 16px; margin-bottom: 8px;
    background: rgba(214,69,69,.12); border: 1px solid rgba(214,69,69,.45);
}
.alert-ok {
    border-radius: 12px; padding: 10px 16px; margin-bottom: 8px;
    background: rgba(46,158,91,.12); border: 1px solid rgba(46,158,91,.45);
}
.hero { text-align: center; padding: 3rem 0 1rem 0; }
.hero h1 { margin-bottom: 0; }
</style>
"""


# ---------- Small helpers ----------

def money(value):
    return f"₹{value:,.0f}"


def card(title, value, sub="", tone="neutral"):
    """One KPI card (HTML)."""
    return (f"<div class='card {tone}'><div class='t'>{html.escape(title)}</div>"
            f"<div class='v'>{html.escape(value)}</div>"
            f"<div class='s'>{html.escape(sub)}</div></div>")


def flash(kind, message):
    """Remember a message to show after the page reloads."""
    st.session_state.flash.append((kind, message))


def init_state():
    st.session_state.setdefault("profile", None)
    st.session_state.setdefault("pending", None)    # duplicate waiting for a decision
    st.session_state.setdefault("flash", [])
    st.session_state.setdefault("form_n", 0)        # changing it gives an empty form


# ---------- Login ----------

def show_login():
    st.markdown("<div class='hero'><h1>💰 Personal Expense Tracker</h1>"
                "<p>Track your spending, check your budget, and see where your money goes.</p></div>",
                unsafe_allow_html=True)
    _, middle, _ = st.columns([1, 2, 1])
    with middle:
        with st.form("login_form"):
            name = st.text_input("Your name", placeholder="e.g. Riya")
            submitted = st.form_submit_button("Continue")
        if submitted:
            try:
                profile, error = db.login(name)
            except Exception:
                st.error("Could not connect to the database. Check your .env file and internet.")
                return
            if error:
                st.error(error)
            else:
                st.session_state.profile = profile
                st.rerun()
        st.caption("No password needed. A new name starts with a sample demo.")


# ---------- Saving an expense ----------

def save_new_expense(owner, row, limit_value):
    """Save the expense and take care of the month's limit. Returns (kind, message)."""
    month = row["date"][:7]
    db.save_expense(owner, row)

    if limit_value is not None:                       # the user typed a limit
        db.save_limit(owner, month, limit_value)
        return "success", f"Expense saved. Limit for {month_label(month)} is now {money(limit_value)}."

    limits = db.get_limits(owner)
    if month not in limits:                           # no limit yet: copy the earlier one
        carried = get_limit_for_month(month, limits)
        if carried is not None:
            db.save_limit(owner, month, carried)
            return "success", (f"Expense saved. The limit for {month_label(month)} was copied "
                               f"from an earlier month ({money(carried)}). You can change it below.")
        return "info", ("Expense saved. No monthly limit is set for "
                        f"{month_label(month)} yet. Enter one in the form to turn on the budget check.")
    return "success", "Expense saved."


def show_add_form(owner):
    n = st.session_state.form_n
    st.subheader("➕ Add expense")
    with st.form(f"add_form_{n}"):
        left, right = st.columns(2)
        with left:
            expense_date = st.date_input("Date", value=date.today(), key=f"date_{n}")
            description = st.text_input("Description", placeholder="e.g. Swiggy", key=f"desc_{n}")
        with right:
            amount = st.text_input("Amount (₹)", placeholder="250   (use - for a refund, like -500)",
                                   key=f"amt_{n}")
            limit_text = st.text_input("Monthly limit for this month (₹)",
                                       placeholder="Leave blank to keep the current limit",
                                       key=f"lim_{n}")
        submitted = st.form_submit_button("Add expense")

    if submitted:
        row, error = clean_expense(expense_date, description, amount)
        if error:
            st.error(error)
        else:
            limit_value = None
            if limit_text.strip() != "":
                limit_value = clean_limit(limit_text)
            if limit_text.strip() != "" and limit_value is None:
                st.error("Monthly limit must be a number above zero")
            elif db.expense_exists(owner, row):
                st.session_state.pending = {"row": row, "limit": limit_value}
            else:
                kind, message = save_new_expense(owner, row, limit_value)
                flash(kind, message)
                st.session_state.form_n += 1
                st.rerun()

    # A duplicate is waiting: ask the user
    pending = st.session_state.pending
    if pending:
        row = pending["row"]
        st.warning(f"This expense already exists: {row['description']}, "
                   f"₹{row['amount']:,.2f} on {row['date']}. Did you buy it again?")
        yes, no, _ = st.columns([1, 1, 4])
        if yes.button("Add anyway", key="dup_yes"):
            kind, message = save_new_expense(owner, row, pending["limit"])
            flash(kind, message)
            st.session_state.pending = None
            st.session_state.form_n += 1
            st.rerun()
        if no.button("Cancel", key="dup_no"):
            st.session_state.pending = None
            st.rerun()


# ---------- Forecast section ----------

def show_forecast(fc, df, month_choice):
    """Forecast graph: spent so far, projection to month end, and the limit."""
    if fc is None:
        st.info("The forecast needs expenses in the current month.")
        return
    if month_choice != "All months" and month_choice != fc["month"]:
        st.info(f"The forecast is only for the current month ({month_label(fc['month'])}). "
                f"Choose All months or {month_label(fc['month'])} to see it.")
        return

    daily = daily_cumulative(df, fc["month"], fc["as_of"])
    days_in_month = fc["days_in_month"]
    days_passed = fc["days_passed"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=daily["day"], y=daily["cumulative"], mode="lines+markers",
                             name="Spent so far", line=dict(color=PALETTE[0], width=3)))
    fig.add_trace(go.Scatter(x=[days_passed, days_in_month], y=[fc["spent"], fc["projected"]],
                             mode="lines+markers", name="Forecast",
                             line=dict(color=PALETTE[1], width=3, dash="dash")))
    if fc["limit"] is not None:
        fig.add_trace(go.Scatter(x=[1, days_in_month], y=[fc["limit"], fc["limit"]],
                                 mode="lines", name="Monthly limit",
                                 line=dict(color=PALETTE[3], width=2, dash="dot")))
    fig.update_layout(height=380, margin=dict(t=10, b=10, l=10, r=10),
                      xaxis_title="Day of the month", yaxis_title="₹",
                      legend=dict(orientation="h", y=1.12))

    chart_col, summary_col = st.columns([2.2, 1])
    with chart_col:
        st.plotly_chart(fig)
    with summary_col:
        if fc["gap"] is None:
            sub, tone = "no limit set", "neutral"
        elif fc["gap"] > 0:
            sub, tone = f"over the limit by {money(fc['gap'])}", "bad"
        else:
            sub, tone = f"{money(-fc['gap'])} under the limit", "ok"
        st.markdown(card("Spent so far", money(fc["spent"]),
                         f"{days_passed} of {days_in_month} days"), unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.markdown(card("Daily average", money(fc["spent"] / days_passed), "per day"),
                    unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.markdown(card(f"Forecast for {month_label(fc['month'])}", money(fc["projected"]),
                         sub, tone), unsafe_allow_html=True)

    note = "Forecast = spent so far ÷ days passed × days in the month."
    if fc["is_fallback"]:
        note += f" Demo: counted up to {fc['as_of'].strftime('%d %b %Y')}."
    st.caption(note)


# ---------- The dashboard ----------

def show_dashboard(owner, using_sample):
    rows = db.get_expenses(owner)
    limits = db.get_limits(owner)
    checks = db.get_budget_check(owner)
    df = to_dataframe(rows)

    if df.empty:
        if using_sample:
            st.error("The sample data is not loaded. Run 02_load.sql in Supabase.")
        else:
            st.info("You have no expenses yet. Add your first expense below, "
                    "and set your monthly limit at the same time.")
        return

    # ----- Filters (sidebar) -----
    months = sorted(df["month"].unique(), reverse=True)
    month_choice = st.sidebar.selectbox(
        "Month", ["All months"] + months,
        format_func=lambda m: m if m == "All months" else month_label(m))
    category_choice = st.sidebar.selectbox(
        "Category", ["All categories"] + sorted(df["category"].unique()))

    by_month = df if month_choice == "All months" else df[df["month"] == month_choice]
    by_category = df if category_choice == "All categories" else df[df["category"] == category_choice]
    filtered = by_month if category_choice == "All categories" \
        else by_month[by_month["category"] == category_choice]

    period = "all months" if month_choice == "All months" else month_label(month_choice)
    cat_text = "all categories" if category_choice == "All categories" else category_choice

    # ----- KPI cards -----
    check_by_month = {c["budget_month"]: c for c in checks}
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(card("Total spend", money(filtered["amount"].sum()),
                         f"{period}, {cat_text}", "neutral"), unsafe_allow_html=True)

    with col2:
        if month_choice == "All months":
            breaches = sum(1 for c in checks if c["status"] == "BREACH")
            st.markdown(card("Months over limit", f"{breaches} of {len(checks)}",
                             "budget check, all months", "bad" if breaches else "ok"),
                        unsafe_allow_html=True)
        else:
            c = check_by_month.get(month_choice)
            if c and c["month_limit"] is not None:
                spent, limit = float(c["spent"]), float(c["month_limit"])
                st.markdown(card("Budget used", f"{spent / limit * 100:.0f}%",
                                 f"{money(spent)} of {money(limit)}",
                                 "bad" if c["status"] == "BREACH" else "ok"),
                            unsafe_allow_html=True)
            else:
                st.markdown(card("Budget used", "No limit", "set one in the form", "neutral"),
                            unsafe_allow_html=True)

    with col3:
        top = category_totals(filtered)
        if top.empty:
            st.markdown(card("Top category", "-", "no expenses", "neutral"), unsafe_allow_html=True)
        else:
            best = top.iloc[0]
            total = filtered["amount"].sum()
            share = f"{best['total'] / total * 100:.0f}% of spend" if total > 0 else ""
            st.markdown(card("Top category", str(best["category"]),
                             f"{money(best['total'])}  {share}", "neutral"), unsafe_allow_html=True)

    with col4:
        fc = forecast(df, limits, date.today(), use_latest_if_none=using_sample)
        if fc is None or (month_choice != "All months" and month_choice != fc["month"]):
            st.markdown(card("Month-end forecast", "-",
                             "only for the current month", "neutral"), unsafe_allow_html=True)
        else:
            if fc["gap"] is None:
                sub, tone = "no limit set", "neutral"
            elif fc["gap"] > 0:
                sub, tone = f"over the limit by {money(fc['gap'])}", "bad"
            else:
                sub, tone = f"{money(-fc['gap'])} under the limit", "ok"
            if fc["is_fallback"]:
                sub += f" (demo, as of {fc['as_of'].strftime('%d %b')})"
            st.markdown(card(f"Forecast for {month_label(fc['month'])}",
                             money(fc["projected"]), sub, tone), unsafe_allow_html=True)

    # ----- Budget alerts -----
    st.subheader("⚠️ Budget alerts")
    shown = [c for c in checks if month_choice == "All months" or c["budget_month"] == month_choice]
    breaches = [c for c in shown if c["status"] == "BREACH"]
    for c in breaches:
        st.markdown(f"<div class='alert-bad'>🔴 <b>{month_label(c['budget_month'])}</b>: spent "
                    f"{money(float(c['spent']))} against a limit of {money(float(c['month_limit']))}, "
                    f"over by <b>{money(float(c['over_by']))}</b>.</div>", unsafe_allow_html=True)
    if not breaches:
        st.markdown("<div class='alert-ok'>🟢 No budget breaches for this selection.</div>",
                    unsafe_allow_html=True)
    for c in shown:
        if c["status"] == "NO LIMIT SET":
            st.info(f"No monthly limit is set for {month_label(c['budget_month'])}.")

    # ----- Monthly trend (full width) -----
    st.divider()
    st.subheader("📈 Monthly trend")
    trend = monthly_totals(by_category)
    labels = [month_label(m) for m in trend["month"]]
    sizes = [14 if m == month_choice else 8 for m in trend["month"]]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=labels, y=trend["total"], mode="lines+markers", name="Spend",
                             line=dict(color=PALETTE[0], width=3), marker=dict(size=sizes)))
    if category_choice == "All categories":
        fig.add_trace(go.Scatter(x=labels, y=[limits.get(m) for m in trend["month"]],
                                 mode="lines", name="Limit",
                                 line=dict(color=PALETTE[3], dash="dash")))
    fig.update_layout(height=380, margin=dict(t=10, b=10, l=10, r=10), yaxis_title="₹",
                      legend=dict(orientation="h", y=1.12))
    st.plotly_chart(fig)
    caption = f"Shows {cat_text}. Follows the Category filter."
    if month_choice != "All months":
        change = change_vs_previous(df, month_choice)
        if change is not None:
            caption += f" {month_label(month_choice)} is {change:+.1f}% compared with the previous month."
    st.caption(caption)

    # ----- Category charts: pie + stacked bar -----
    st.divider()
    left, right = st.columns([1, 1.3])

    with left:
        st.subheader("🥧 Spend by category")
        pie_data = category_totals(by_month)
        pie_data = pie_data[pie_data["total"] > 0]
        if pie_data.empty:
            st.info("Nothing to show for this month.")
        else:
            fig = px.pie(pie_data, names="category", values="total", hole=0.45,
                         color_discrete_sequence=PALETTE)
            fig.update_traces(textinfo="percent+label")
            fig.update_layout(height=420, margin=dict(t=10, b=10, l=10, r=10), showlegend=False)
            st.plotly_chart(fig)
        st.caption(f"Shows {period}. Follows the Month filter.")

    with right:
        st.subheader("📊 Category spend by month")
        stacked = category_by_month(df)
        stacked["label"] = stacked["month"].map(month_label)
        order = [month_label(m) for m in sorted(df["month"].unique())]
        fig = px.bar(stacked, x="label", y="amount", color="category", barmode="stack",
                     category_orders={"label": order}, color_discrete_sequence=PALETTE)
        fig.update_layout(height=420, margin=dict(t=10, b=10, l=10, r=10),
                          xaxis_title="", yaxis_title="₹",
                          legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(fig)
        st.caption("Shows all months, split by category.")

    # ----- Forecast graph -----
    st.divider()
    st.subheader("🔮 Month-end forecast")
    show_forecast(fc, df, month_choice)

    st.divider()
    # ----- Drill-down: the expenses behind the numbers -----
    with st.expander(f"🔎 Expense details ({len(filtered)} rows: {period}, {cat_text})"):
        view = filtered.sort_values("date", ascending=False).copy()
        view["date"] = view["date"].dt.strftime("%Y-%m-%d")
        view = view[["date", "description", "amount", "category"]]
        view.columns = ["Date", "Description", "Amount (₹)", "Category"]
        st.dataframe(view, hide_index=True)


# ---------- Main ----------

def main():
    st.markdown(CSS, unsafe_allow_html=True)
    init_state()

    profile = st.session_state.profile
    if profile is None:
        show_login()
        return

    user = profile["user_name"]
    using_sample = profile["show_sample"]
    owner = "sample" if using_sample else user

    # ----- Sidebar -----
    with st.sidebar:
        st.markdown(f"### 👤 {profile['display_name']}")
        st.caption("Viewing: sample data" if using_sample else "Viewing: your own data")
        if not using_sample:
            if st.button("Show sample data again"):
                db.set_show_sample(user, True)
                profile["show_sample"] = True
                st.rerun()
        if st.button("Log out"):
            st.session_state.profile = None
            st.session_state.pending = None
            st.session_state.flash = []
            st.rerun()
        st.divider()

    # ----- Header -----
    st.title("💰 Personal Expense Dashboard")

    for kind, message in st.session_state.flash:
        {"success": st.success, "info": st.info}.get(kind, st.info)(message)
    st.session_state.flash = []

    if using_sample:
        st.markdown("<div class='banner'>📊 You are viewing <b>sample data</b>, "
                    "only for demonstration.</div>", unsafe_allow_html=True)
        if st.button("Remove sample data and use my own expenses", type="primary"):
            db.set_show_sample(user, False)
            profile["show_sample"] = False
            flash("info", "Sample data removed. This is your own dashboard now. "
                          "Add your first expense below.")
            st.rerun()

    show_dashboard(owner, using_sample)

    if not using_sample:
        st.divider()
        show_add_form(owner)


try:
    main()
except Exception as error:
    st.error(f"Something went wrong: {error}")