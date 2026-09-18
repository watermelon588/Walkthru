-- Applied by: .venv/Scripts/python -m app.db   (idempotent; re-run after edits)
-- The API writes with the postgres role (bypasses RLS). Browsers read through RLS with the user's JWT.

create table if not exists public.runs (
  id text primary key,
  user_id uuid not null references auth.users (id) on delete cascade,
  site text not null,
  goal text not null,
  persona text not null,
  tier text not null default 'free',
  logged_in boolean not null default false,
  status text not null default 'running',
  steps jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists runs_user_created on public.runs (user_id, created_at desc);

alter table public.runs enable row level security;

drop policy if exists "owner reads runs" on public.runs;
create policy "owner reads runs" on public.runs
  for select to authenticated
  using (user_id = (select auth.uid()));

grant select on public.runs to authenticated;

-- Instant scans (no account) and reports. Added 2026-09-18.
alter table public.runs alter column user_id drop not null;
alter table public.runs add column if not exists kind text not null default 'test';      -- test | scan
alter table public.runs add column if not exists report jsonb;
alter table public.runs add column if not exists public boolean not null default false;
alter table public.runs add column if not exists email text;
alter table public.runs add column if not exists tokens integer not null default 0;

drop policy if exists "anyone reads public runs" on public.runs;
create policy "anyone reads public runs" on public.runs
  for select to anon, authenticated
  using (public = true);

grant select on public.runs to anon;
