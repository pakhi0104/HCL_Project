-- 03_views.sql
-- Views = saved queries that behave like ready-made tables.
-- Every view has an OWNER column; the dashboard filters it: where owner = 'riya'.
-- Run after 01_ddl.sql and 02_load.sql.

-- View 1: one row per owner per month, with the limit and status
create or replace view monthly_summary as
select
    e.owner                                         as owner,
    to_char(e.expense_date, 'YYYY-MM')              as month,
    sum(e.amount)                                   as total_spend,
    b.limit_amount                                  as limit_amount,
    round(100 * sum(e.amount) / b.limit_amount, 1)  as used_pct,
    sum(e.amount) - b.limit_amount                  as over_by,   -- negative = money left
    sum(e.amount) > b.limit_amount                  as is_breach
from expenses e
left join budget b
       on b.owner = e.owner
      and b.month = to_char(e.expense_date, 'YYYY-MM')
group by e.owner, to_char(e.expense_date, 'YYYY-MM'), b.limit_amount;

-- View 2: spend per category per month (feeds the pie chart)
create or replace view category_monthly as
select
    owner,
    to_char(expense_date, 'YYYY-MM')  as month,
    category,
    sum(amount)                       as total_spend,
    count(*)                          as num_expenses
from expenses
group by owner, to_char(expense_date, 'YYYY-MM'), category;

-- View 3: each month compared with the previous month (feeds the trend line)
create or replace view month_over_month as
select
    owner,
    month,
    total_spend,
    lag(total_spend) over (partition by owner order by month) as prev_spend,
    round(
        100 * (total_spend - lag(total_spend) over (partition by owner order by month))
            / nullif(lag(total_spend) over (partition by owner order by month), 0),
        1
    ) as change_pct
from (
    select owner,
           to_char(expense_date, 'YYYY-MM') as month,
           sum(amount)                      as total_spend
    from expenses
    group by owner, to_char(expense_date, 'YYYY-MM')
) as t;

-- Check: monthly summary of the sample data
select * from monthly_summary where owner = 'sample' order by month;