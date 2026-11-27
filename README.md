# 💰 Personal Expense Tracker and Budget Dashboard

A multi-user expense tracker that cleans and categorises expenses, stores them in a database, flags months that go over their spending limit, and shows everything on an interactive dashboard with a month-end forecast.

**🔗 Live app:** https://hclproject-jnggj8t8kpcqckqmgitqm8.streamlit.app/

**🎥 Demo video:** https://drive.google.com/file/d/1qhsikLkaT2zf4bbYPrYtwnC7EpaZJLFg/view?usp=drivesdk

> **Note on tools:** This project uses **Streamlit** for the dashboard (instead of Power BI) and **Supabase / PostgreSQL with PL/pgSQL** for the database and budget check (instead of Oracle with PL/SQL).

---

## 1. Problem Statement

Many people record their expenses in scattered notes, apps, or bank statements, so they cannot easily see where their money goes each month. Without clear categories, correct handling of refunds, and a monthly spending limit, overspending is noticed only after the month has ended.

This project builds a system where users log in with a name, enter expenses through a form, and get cleaned and categorised data, a database budget check, and a dashboard with charts and a month-end forecast. A built-in sample demo lets new users see how everything works before entering their own data.

## 2. Objectives and Results

| # | Objective | Result |
|---|---|---|
| 1 | Monthly totals on the dashboard match the source data | ✅ Matches the data-quality report and database queries exactly |
| 2 | At least 90% of expenses categorised automatically | ✅ 94% (7 of 109 sample rows are "Uncategorised") |
| 3 | Database check flags every month over its limit | ✅ September 2026 flagged as BREACH |
| 4 | Dashboard has pie chart, trend line, extra chart, forecast, and filters | ✅ Done |
| 5 | New expenses appear without re-running any script | ✅ Done (saved to the database, dashboard reloads) |
| 6 | Each user sees only their own data | ✅ Each row has an owner; the sample demo is shared and read-only |

## 3. Features

- **Name-only login** (no password). A new name starts with the sample demo.
- **Sample demo** with a button: *"Remove sample data and use my own expenses"*. After that, the user has an empty dashboard of their own.
- **Add expense form:** date, description, amount (negative = refund), and the monthly limit.
- **Automatic cleaning and categorisation** of every expense (from the sample CSV and from the form).
- **Duplicate handling:** dropped silently in the sample CSV. In the form, the user sees *"already exists, add anyway or cancel"*.
- **Monthly limit** per user and per month. If left blank, the earlier month's limit is copied.
- **Budget check** in the database (PL/pgSQL) that flags each month as OK or BREACH.
- **Dashboard:** KPI cards, budget alerts, monthly trend with limit line, category pie chart, category-by-month stacked bars, a month-end forecast graph, filters for month and category, and a drill-down list of the expenses behind the numbers.

## 4. Architecture

```
generate_data.py ─► expenses_raw.csv ─► clean_data.py ─► expenses_clean.csv ─► 02_load.sql ─┐
                                                                                            ▼
Streamlit dashboard (app.py)  ◄──── db.py (Supabase API) ◄────  Supabase: tables, views, check_budget()
        │                                                                  ▲
        └── Add expense form ─► clean_expense() ─► duplicate check ─► save ┘
```

The same function, `clean_expense()`, is the gatekeeper for the sample CSV and for every form entry, so all data is treated the same way.

## 5. Tech Stack

| Tool | Purpose |
|---|---|
| Python (pandas) | Data generation, cleaning, categorisation, calculations |
| Supabase (PostgreSQL), SQL, PL/pgSQL | Tables, views, budget-check function |
| supabase-py, python-dotenv | Connecting Python to the database; keys kept in `.env` |
| Streamlit, Plotly, CSS | Dashboard, charts, form |
| GitHub, Streamlit Community Cloud | Code hosting and deployment |

## 6. Data

**Sample data:** self-generated with a fixed random seed (repeatable). 114 raw expenses from June to November 2026, deliberately messy.

**Data-quality report** (from `clean_data.py`):

| Check | Count |
|---|---|
| Rows in raw file | 114 |
| Rejected (missing or invalid amount) | 1 |
| Duplicates removed | 4 |
| Descriptions fixed (spaces / capitals) | 14 |
| Dates converted to standard format | 2 |
| **Final clean rows** | **109** |
| Uncategorised | 7 (6.4%) |
| Refund entries | 5 |

**Monthly totals and budget check** (limit ₹18,000 per month for the sample data):

| Month | Spend (₹) | Status |
|---|---|---|
| Jun 2026 | 16,688 | OK |
| Jul 2026 | 16,888 | OK |
| Aug 2026 | 16,888 | OK |
| Sep 2026 | 22,838 | **BREACH** (over by ₹4,838) |
| Oct 2026 | 17,958 | OK (₹42 under) |
| Nov 2026 (to 25th) | 17,578 | OK so far |

## 8. KPI Definitions

| KPI | Formula |
|---|---|
| Total Monthly Spend | Sum of amounts in the month (refunds are negative, so they reduce it) |
| Category Spend | Sum of amounts per category and month |
| Category Share % | Category spend ÷ total spend × 100 |
| Budget Used % | Month spend ÷ monthly limit × 100 |
| Budget Breach | Yes if month spend > monthly limit |
| Breach Count | Number of months over their limit |
| Month-over-Month Change % | (This month − last month) ÷ last month × 100 |
| Month-End Forecast | (Spent so far ÷ days passed) × days in the month |
| Forecast Gap | Forecast − monthly limit (positive = overshoot) |

## 9. Test Cases

| Test case | Expected | Result |
|---|---|---|
| Uncategorised expense | Becomes "Uncategorised", nothing crashes | ✅ 7 rows |
| Refund entries | Negative amount reduces the category and month total | ✅ 5 rows |
| Month-end boundary dates | 30/31 of a month and 1st of the next land in the correct months | ✅ Verified with SQL query |
| Messy text, bad dates, missing amount | Fixed or rejected, counted in the report | ✅ |
| Duplicate in form | User is asked before saving | ✅ |

Run the automated tests:

```
python clean_data.py test
python test_analysis.py
```

## 10. Project Structure

```
├── app.py                  # Streamlit dashboard
├── analysis.py             # Totals, change %, forecast calculations
├── clean_data.py           # Cleaning, categorisation, duplicate and limit checks
├── db.py                   # Supabase connection and database functions
├── 02_load.sql
├── generate_data.py        # Creates expenses_raw.csv and budget.csv
├── Make_loade.py        # Builds 02_load.sql from the clean CSVs
├── test_connection.py      # Checks the database connection
├── test_analysis.py        # Tests the dashboard calculations           # (optional) deletes old tables and views
├── SQL_Queries            # A folder that contains all the sql/pgsql queries to run in Supabase Database editor
├── expenses_raw.csv, expenses_clean.csv, budget.csv
├── data_quality_report.txt
├── requirements.txt
```

## 11. How to Run Locally

**Requirements:** Python 3.12 or 3.13 (recommended), a free Supabase account.

**1. Get the code and install libraries**

```
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

**2. Set up the database (Supabase)**

- In your project's settings, keep the Data API on and let new tables be exposed to the API. Leave Row Level Security off for new tables (see Limitations).
- Open the **SQL Editor** and run these files, pasting the whole file each time and in this order: `01_ddl.sql`, `02_load.sql`, `03_views.sql`, `05_budget_check.sql`. (Run `00_reset.sql` first only if you used an older version.)
- Check: `select * from check_budget('sample');` should show September as BREACH.
- `04_queries.sql` holds example queries. Run them one at a time.

**3. Add your keys**

Copy `.env.example` to a new file named `.env` and fill in your project URL and **publishable** key:

```
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-publishable-key
```

Never commit `.env`, and never use the secret key.

**4. Test and run**

```
python test_connection.py
python -m streamlit run app.py
```

**Regenerate the sample data (optional):**

```
python generate_data.py
python clean_data.py
python make_load_sql.py
```

## 12. Deployment

The app is deployed on **Streamlit Community Cloud** from this GitHub repository (main file: `app.py`). The two keys are added in the app's **Secrets** in TOML format, with quotes:

```
SUPABASE_URL = "https://your-project-id.supabase.co"
SUPABASE_KEY = "your-publishable-key"
```

## 14. Insights (sample data)

- September 2026 is the only month over the ₹18,000 limit: ₹22,838, which is ₹4,838 over.
- October came within ₹42 of the limit, and the other months stayed between about ₹16,700 and ₹17,600.
- <add 2 or 3 category insights from your dashboard, for example the biggest category and its share>

## 15. Known Limitations

- **Name-only login has no password.** Anyone who types a name sees that user's data, and two people with the same name share data. It is meant for a demo, not for private financial data.
- **The database API is open to anyone with the publishable key** (Row Level Security is off, because there are no user accounts). Keys are kept out of GitHub through `.env`.
- The forecast is a simple daily average, not a prediction model.
- A genuine repeat purchase on the same day looks like a duplicate, so the form asks before saving it.
