-- Automated agent nudges (written by the daily sweep, read by the UI)
-- Run this once in the Supabase SQL Editor.
create table if not exists agent_nudges (
  id                  uuid primary key default gen_random_uuid(),
  user_id             text not null,
  created_at          timestamptz not null default now(),
  nudge_type          text not null check (nudge_type in ('wellbeing', 'reengage')),
  message             text not null,
  concerning_metrics  jsonb,
  run_id              text
);
create index if not exists idx_agent_nudges_user_time
  on agent_nudges (user_id, created_at desc);
