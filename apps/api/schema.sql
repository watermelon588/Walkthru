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
alter table public.runs add column if not exists tokens integer not null default 0;

drop policy if exists "anyone reads public runs" on public.runs;
create policy "anyone reads public runs" on public.runs
  for select to anon, authenticated
  using (public = true);

grant select on public.runs to anon;

-- Private journey screenshots. Objects are scoped by run id: <run_id>/step-01.jpg.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('run-evidence', 'run-evidence', false, 1500000, array['image/jpeg'])
on conflict (id) do update set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists "owners upload run evidence" on storage.objects;
create policy "owners upload run evidence" on storage.objects
  for insert to authenticated
  with check (
    bucket_id = 'run-evidence'
    and exists (
      select 1 from public.runs
      where runs.id = split_part(name, '/', 1)
        and runs.user_id = (select auth.uid())
    )
  );

drop policy if exists "owners and public reports read run evidence" on storage.objects;
create policy "owners and public reports read run evidence" on storage.objects
  for select to anon, authenticated
  using (
    bucket_id = 'run-evidence'
    and exists (
      select 1 from public.runs
      where runs.id = split_part(name, '/', 1)
        and (runs.user_id = (select auth.uid()) or runs.public = true)
    )
  );

-- Evidence retention (2026-09-23): screenshots expire, runs and reports stay until the owner deletes them.
alter table public.runs add column if not exists evidence_purged_at timestamptz;
create index if not exists runs_evidence_retention on public.runs (created_at) where kind = 'test' and evidence_purged_at is null;

-- Paid passes (2026-09-24, SPEC.md "Plans"). The API reads the active row to decide the caller's plan.
-- Rows come from the founder (V1 concierge), a verified Dodo webhook, promos, or scripts/grant_plan.py in development.
create table if not exists public.entitlements (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  plan text not null check (plan in ('launch', 'pro', 'plus')),
  starts_at timestamptz not null default now(),
  expires_at timestamptz not null,
  runs_granted integer not null check (runs_granted >= 0),
  source text not null check (source in ('founder', 'dodo', 'promo', 'dev')),
  created_at timestamptz not null default now()
);

create index if not exists entitlements_user_expires on public.entitlements (user_id, expires_at desc);

alter table public.entitlements enable row level security;

drop policy if exists "owner reads entitlements" on public.entitlements;
create policy "owner reads entitlements" on public.entitlements
  for select to authenticated
  using (user_id = (select auth.uid()));

grant select on public.entitlements to authenticated;

-- Ignored findings (2026-09-24, paid plans). Kept per site origin, so an ignored finding stays ignored on reruns.
create table if not exists public.finding_states (
  user_id uuid not null references auth.users (id) on delete cascade,
  origin text not null,
  fingerprint text not null,
  reason text not null,
  created_at timestamptz not null default now(),
  primary key (user_id, origin, fingerprint)
);

alter table public.finding_states enable row level security;

drop policy if exists "owner reads finding states" on public.finding_states;
create policy "owner reads finding states" on public.finding_states
  for select to authenticated
  using (user_id = (select auth.uid()));

grant select on public.finding_states to authenticated;

-- 2026-09-25: contact emails never live in runs. Public reports are readable with the public key, so an email
-- column there leaked Instant Scan and owner addresses. The API now sends report emails without storing them.
alter table public.runs drop column if exists email;
notify pgrst, 'reload schema';

-- 2026-09-25: personal API keys for the MCP server (Plus). Shown once, stored as SHA-256, revocable.
-- RLS on and no grants: only the API (service role) reads or writes this table.
create table if not exists public.api_keys (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  name text not null check (char_length(name) between 1 and 60),
  key_hash text not null unique,
  created_at timestamptz not null default now(),
  last_used_at timestamptz,
  revoked_at timestamptz
);
alter table public.api_keys enable row level security;
revoke all on public.api_keys from anon, authenticated;  -- belt and braces: RLS has no policies either
create index if not exists api_keys_user on public.api_keys (user_id) where revoked_at is null;
notify pgrst, 'reload schema';
