-- 05_budget_check.sql
-- The budget check, written in PL/pgSQL (PostgreSQL's version of Oracle's PL/SQL).
-- For ONE owner, it goes through every month, compares the month's spending with
-- that month's limit, and flags a BREACH when spending is more than the limit.
--
-- Use:
--   select * from check_budget('sample');            -- all months of the sample data
--   select * from check_budget('riya');              -- all months of user riya
--   select * from check_budget('riya', '2026-12');   -- one month only

create or replace function check_budget(p_owner text, p_month text default null)
returns table (
    budget_month text,      -- like '2026-09'
    spent        numeric,   -- net spend of the month (refunds subtracted)
    month_limit  numeric,   -- the limit of that month
    over_by      numeric,   -- spent - limit (positive = over, negative = money left)
    status       text       -- 'BREACH', 'OK' or 'NO LIMIT SET'
)
language plpgsql
as $$
declare
    r record;
begin
    -- Loop over every month in which this owner has expenses
    for r in
        select to_char(e.expense_date, 'YYYY-MM') as m,
               sum(e.amount)                      as total
        from expenses e
        where e.owner = p_owner
          and (p_month is null or to_char(e.expense_date, 'YYYY-MM') = p_month)
        group by to_char(e.expense_date, 'YYYY-MM')
        order by 1
    loop
        budget_month := r.m;
        spent        := r.total;

        -- Look up the limit of this owner for this month (stays empty if none)
        select b.limit_amount into month_limit
        from budget b
        where b.owner = p_owner
          and b.month = r.m;

        if month_limit is null then
            over_by := null;
            status  := 'NO LIMIT SET';
        elsif spent > month_limit then
            over_by := spent - month_limit;
            status  := 'BREACH';
        else
            over_by := spent - month_limit;
            status  := 'OK';
        end if;

        return next;       -- send this row to the result
    end loop;
end;
$$;

-- Check: run the budget check on the sample data
select * from check_budget('sample');