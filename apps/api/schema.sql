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

-- 2026-09-25: weekly watch (Plus). One row per watched site; the API checks due rows weekly and on a deploy hook.
-- Runs gain two kinds: 'watch' (a watch check, a normal report) and 'compare' (competitor side by side).
create table if not exists public.sites (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  site text not null,
  watch boolean not null default true,
  hook_hash text unique,
  last_run_id text,
  last_changes jsonb,
  next_check_at timestamptz not null default now(),
  last_hook_at timestamptz,
  created_at timestamptz not null default now(),
  unique (user_id, site)
);
alter table public.sites enable row level security;
revoke all on public.sites from anon, authenticated;
create index if not exists sites_due on public.sites (next_check_at) where watch;

-- ---------- V10 billing (2026-09-25, payment.md) ----------
-- Founder-approved 30-day passes paid through Dodo. Nothing here is writable from a browser: the API and the
-- founder's scripts write with the secret key. Owners may read their own requests and offers; webhook events and
-- the admin audit log are server-only. Supabase grants new public tables to anon/authenticated by default, so
-- every table below revokes that first and grants back only what a policy allows.

-- A signed-in user asks for paid access. At most one pending request per user.
create table if not exists public.access_requests (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  plan text not null check (plan in ('launch', 'pro', 'plus')),
  note text not null default '' check (char_length(note) <= 500),
  status text not null default 'pending' check (status in ('pending', 'approved', 'rejected')),
  created_at timestamptz not null default now(),
  decided_at timestamptz
);
create unique index if not exists access_requests_one_pending on public.access_requests (user_id) where status = 'pending';
create index if not exists access_requests_user_created on public.access_requests (user_id, created_at desc);

-- The founder's immutable offer: exact plan, price, product, runs and days, bound to one user.
-- Checkout is possible only while status = 'approved' and before checkout_expires_at (24 hours).
create table if not exists public.billing_offers (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  request_id uuid references public.access_requests (id) on delete set null,
  plan text not null check (plan in ('launch', 'pro', 'plus')),
  founding boolean not null default false,
  price_cents integer not null check (price_cents > 0),
  currency text not null default 'USD',
  product_id text not null,
  runs integer not null check (runs > 0),
  days integer not null check (days between 1 and 31),
  status text not null default 'approved' check (status in ('approved', 'paid', 'cancelled', 'refunded')),
  checkout_expires_at timestamptz not null,
  payment_id text unique,
  paid_at timestamptz,
  approved_by text not null,
  created_at timestamptz not null default now()
);
create index if not exists billing_offers_user_created on public.billing_offers (user_id, created_at desc);

-- Every verified Dodo webhook, once. The webhook-id primary key makes redelivery a no-op.
create table if not exists public.billing_events (
  webhook_id text primary key,
  event_type text not null,
  object_id text,
  body_sha256 text not null,
  received_at timestamptz not null default now(),
  processed_at timestamptz,
  result text
);

-- Founder actions: approvals, rejections, offers, cancellations.
create table if not exists public.admin_audit_log (
  id bigint generated always as identity primary key,
  actor text not null,
  action text not null,
  target text not null,
  detail jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

-- A pass bought through Dodo points at its offer and payment; each can grant at most one pass.
alter table public.entitlements add column if not exists offer_id uuid unique references public.billing_offers (id) on delete set null;
alter table public.entitlements add column if not exists payment_id text unique;
alter table public.entitlements add column if not exists revoked_at timestamptz;
alter table public.entitlements add column if not exists revoked_reason text;
-- Passes are money: browsers may only read them (RLS already blocks writes; this removes the privilege too).
revoke insert, update, delete, truncate on public.entitlements from anon, authenticated;

alter table public.access_requests enable row level security;
alter table public.billing_offers enable row level security;
alter table public.billing_events enable row level security;
alter table public.admin_audit_log enable row level security;
revoke all on public.access_requests, public.billing_offers, public.billing_events, public.admin_audit_log from anon, authenticated;

drop policy if exists "owner reads access requests" on public.access_requests;
create policy "owner reads access requests" on public.access_requests
  for select to authenticated
  using (user_id = (select auth.uid()));
grant select on public.access_requests to authenticated;

drop policy if exists "owner reads billing offers" on public.billing_offers;
create policy "owner reads billing offers" on public.billing_offers
  for select to authenticated
  using (user_id = (select auth.uid()));
grant select on public.billing_offers to authenticated;

notify pgrst, 'reload schema';
