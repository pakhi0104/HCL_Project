-- 01_ddl.sql
-- Creates the 4 tables of the Expense Tracker (Supabase / PostgreSQL).
-- Every expense and every limit has an OWNER: 'sample' for the demo data,
-- or the user's name (lowercase) for a real user.

-- Table 1: category (the list of allowed categories)
create table category (
    category_name text primary key
);

insert into category (category_name) values
    ('Food'), ('Travel'), ('Shopping'), ('Rent'), ('Entertainment'),
    ('Bills'), ('Health'), ('Education'), ('Uncategorised');

-- Table 2: profiles (one row per user, found by the name they type at login)
create table profiles (
    user_name    text primary key,                 -- lowercase, trimmed, like 'riya'
    display_name text    not null,                 -- as typed, like 'Riya'
    show_sample  boolean not null default true,    -- true = still showing the demo data
    created_at   timestamptz not null default now()
);

-- The demo data belongs to a special profile called 'sample'
insert into profiles (user_name, display_name, show_sample)
values ('sample', 'Sample Data', false);

-- Table 3: budget (one spending limit per owner per month, month like '2026-06')
create table budget (
    owner        text not null references profiles (user_name),
    month        text not null check (month ~ '^[0-9]{4}-[0-9]{2}$'),
    limit_amount numeric(12,2) not null check (limit_amount > 0),
    primary key (owner, month)
);

-- Table 4: expenses (every expense of every owner; refunds are negative)
create table expenses (
    expense_id   bigint generated always as identity primary key,
    owner        text          not null references profiles (user_name),
    expense_date date          not null,
    description  text          not null,
    amount       numeric(12,2) not null check (amount <> 0),
    category     text          not null references category (category_name)
);

-- Makes "all expenses of one owner" queries fast
create index idx_expenses_owner_date on expenses (owner, expense_date);