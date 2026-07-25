-- schema.sql — Student Wellbeing Agent
-- Run this ONCE in your Supabase project: Dashboard → SQL Editor → paste → Run.
-- Safe to re-run: uses IF NOT EXISTS everywhere.
--
-- Matches api/db.py exactly. The backend uses the service-role key, which
-- bypasses RLS — so we enable RLS with no public policies, meaning the anon
-- key can read NOTHING. Private by default.

create table if not exists users (
    id uuid primary key,
    phq2_score int not null,
    gad2_score int not null,
    pss4_score int not null,
    overall_risk text not null,
    onboarding_raw_responses jsonb,
    created_at timestamptz default now()
);

create table if not exists daily_logs (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references users(id) on delete cascade,
    log_date date not null,
    mood int not null,
    sleep_hours float not null,
    sleep_quality int not null,
    study_hours float not null,
    stress int not null,
    free_text text,
    created_at timestamptz default now(),
    unique (user_id, log_date)
);

create table if not exists flags (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references users(id) on delete cascade,
    flag_date date not null,
    flag_type text not null,
    triggering_metrics jsonb,
    reason text,
    resolved boolean default false,
    created_at timestamptz default now()
);

create table if not exists safety_checks (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references users(id) on delete cascade,
    check_date date not null,
    trigger_source text not null,
    item9_response int not null,
    crisis_path_fired boolean not null,
    resources_shown jsonb,
    created_at timestamptz default now()
);

create index if not exists idx_daily_logs_user_date on daily_logs (user_id, log_date);
create index if not exists idx_flags_user_date on flags (user_id, flag_date);

-- Lock everything down for the anon key (backend service-role key bypasses RLS)
alter table users enable row level security;
alter table daily_logs enable row level security;
alter table flags enable row level security;
alter table safety_checks enable row level security;
