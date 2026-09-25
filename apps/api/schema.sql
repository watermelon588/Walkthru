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

-- ---------- Plus: custom test users and several test users per report (P4.2), branded PDF (P4.3), 2026-09-25 ----------
-- API-only tables (service role): browsers never read or write them directly.

-- A test user the owner describes in their own words. The run stores its name in runs.persona, so every page that
-- shows a built-in test user's label shows this name the same way.
create table if not exists public.test_users (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  name text not null check (char_length(name) between 1 and 40),
  description text not null check (char_length(description) between 10 and 300),
  created_at timestamptz not null default now(),
  unique (user_id, name)
);
alter table public.test_users enable row level security;
revoke all on public.test_users from anon, authenticated;

-- Several test users on one goal: their runs share a group id, and each report shows the group side by side.
alter table public.runs add column if not exists group_id uuid;
create index if not exists runs_group on public.runs (group_id) where group_id is not null;

-- The owner's branding for printed reports: name, logo (a small PNG, JPEG or WebP data URL), color, footer line.
create table if not exists public.report_brands (
  user_id uuid primary key references auth.users (id) on delete cascade,
  name text not null check (char_length(name) between 1 and 80),
  color text not null default '#1b1b1f' check (color ~ '^#[0-9a-f]{6}$'),
  footer text not null default '' check (char_length(footer) <= 120),
  logo text check (logo is null or char_length(logo) <= 300000),
  updated_at timestamptz not null default now()
);
alter table public.report_brands enable row level security;
revoke all on public.report_brands from anon, authenticated;

notify pgrst, 'reload schema';

-- ---------- Plus: team workspaces (2026-09-25, docs/team-collaboration.md) ----------
-- A Plus owner's workspace: members, invitations, shared reports, finding triage, chat and an activity log.
-- The API writes every row with the secret key after checking the caller's membership and role on each request.
-- Browsers only read, and only rows of workspaces they belong to: Supabase Realtime needs these select policies to
-- push chat and activity live. No team table grants insert, update or delete to a browser role.

create table if not exists public.teams (
  id uuid primary key default gen_random_uuid(),
  name text not null check (char_length(name) between 1 and 60),
  owner_id uuid not null references auth.users (id) on delete cascade,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists teams_owner on public.teams (owner_id);

-- name and email are a display copy of the member's profile, refreshed when they open the workspace.
create table if not exists public.team_members (
  team_id uuid not null references public.teams (id) on delete cascade,
  user_id uuid not null references auth.users (id) on delete cascade,
  role text not null check (role in ('owner', 'admin', 'member', 'viewer')),
  name text not null default '' check (char_length(name) <= 80),
  email text not null default '' check (char_length(email) <= 320),
  auto_share boolean not null default false,
  last_read_message_id bigint not null default 0,
  last_seen_at timestamptz,
  joined_at timestamptz not null default now(),
  primary key (team_id, user_id)
);
create index if not exists team_members_user on public.team_members (user_id);
create unique index if not exists team_members_one_owner on public.team_members (team_id) where role = 'owner';

-- Email invitations (one address, one use) and invite links (a join code, several uses, optional email domain).
-- Only the SHA-256 of a code is stored. API only: no browser grants and no policies.
create table if not exists public.team_invites (
  id uuid primary key default gen_random_uuid(),
  team_id uuid not null references public.teams (id) on delete cascade,
  kind text not null check (kind in ('email', 'link')),
  token_hash text not null unique,
  email text check (email is null or char_length(email) <= 320),
  email_domain text check (email_domain is null or char_length(email_domain) <= 253),
  role text not null check (role in ('admin', 'member', 'viewer')),
  max_uses integer not null default 1 check (max_uses between 1 and 100),
  uses integer not null default 0 check (uses >= 0),
  invited_by uuid references auth.users (id) on delete set null,
  invited_by_name text not null default '',
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  revoked_at timestamptz,
  check ((kind = 'email') = (email is not null)),
  check (kind = 'link' or max_uses = 1),
  check (kind = 'email' or role <> 'admin')
);
create index if not exists team_invites_team on public.team_invites (team_id) where revoked_at is null;
create index if not exists team_invites_email on public.team_invites (email) where kind = 'email' and revoked_at is null;

-- A report shared into a workspace. Deleting the run removes it from every workspace.
create table if not exists public.team_runs (
  team_id uuid not null references public.teams (id) on delete cascade,
  run_id text not null references public.runs (id) on delete cascade,
  shared_by uuid references auth.users (id) on delete set null,
  shared_at timestamptz not null default now(),
  primary key (team_id, run_id)
);
create index if not exists team_runs_run on public.team_runs (run_id);
create index if not exists team_runs_team_shared on public.team_runs (team_id, shared_at desc);

-- Triage of a finding across the workspace's reports, keyed like ignored findings: site origin plus fingerprint.
create table if not exists public.team_findings (
  team_id uuid not null references public.teams (id) on delete cascade,
  origin text not null check (char_length(origin) <= 300),
  fingerprint text not null check (char_length(fingerprint) <= 300),
  status text not null default 'open' check (status in ('open', 'in_progress', 'fixed', 'wont_fix')),
  assignee_id uuid references auth.users (id) on delete set null,
  updated_by uuid references auth.users (id) on delete set null,
  updated_at timestamptz not null default now(),
  primary key (team_id, origin, fingerprint)
);

-- Chat. thread 'general' is the workspace channel; 'run:<id>' and 'finding:<key>' are comment threads.
-- client_id makes a retried send land once. A deleted message keeps its row with an empty body.
create table if not exists public.team_messages (
  id bigint generated always as identity primary key,
  team_id uuid not null references public.teams (id) on delete cascade,
  thread text not null default 'general' check (thread ~ '^(general|run:[0-9a-f]{32}|finding:[0-9a-f]{32})$'),
  author_id uuid references auth.users (id) on delete set null,
  author_name text not null default '' check (char_length(author_name) <= 80),
  body text not null check (char_length(body) <= 4000),
  mentions uuid[] not null default '{}',
  client_id uuid not null default gen_random_uuid(),
  created_at timestamptz not null default now(),
  edited_at timestamptz,
  deleted_at timestamptz,
  unique (team_id, client_id)
);
create index if not exists team_messages_thread on public.team_messages (team_id, thread, id);

-- Activity feed and audit trail: who joined, shared, triaged, invited or changed a role.
create table if not exists public.team_events (
  id bigint generated always as identity primary key,
  team_id uuid not null references public.teams (id) on delete cascade,
  actor_id uuid references auth.users (id) on delete set null,
  actor_name text not null default '' check (char_length(actor_name) <= 80),
  type text not null check (char_length(type) <= 40),
  detail jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists team_events_team on public.team_events (team_id, id desc);

-- Membership checks for row-level security. SECURITY DEFINER so a policy never recurses into team_members' own
-- policy; both only ever answer for the caller (auth.uid()).
create or replace function public.is_team_member(p_team uuid) returns boolean
  language sql stable security definer set search_path = ''
  as $$ select exists (select 1 from public.team_members m where m.team_id = p_team and m.user_id = (select auth.uid())) $$;

create or replace function public.shared_with_me(p_run text) returns boolean
  language sql stable security definer set search_path = ''
  as $$ select exists (select 1 from public.team_runs r join public.team_members m on m.team_id = r.team_id
                       where r.run_id = p_run and m.user_id = (select auth.uid())) $$;

revoke all on function public.is_team_member(uuid), public.shared_with_me(text) from public, anon;
grant execute on function public.is_team_member(uuid), public.shared_with_me(text) to authenticated;

-- Joining is one locked transaction, so two people can never take the last seat at once.
-- Returns joined, member (already in), invalid (revoked, expired or used up), full (no seat) or limit (too many workspaces).
create or replace function public.team_join(p_invite uuid, p_user uuid, p_name text, p_email text, p_seats integer, p_max_teams integer)
  returns text language plpgsql set search_path = ''
as $$
declare
  inv public.team_invites%rowtype;
  taken integer;
begin
  select * into inv from public.team_invites where id = p_invite for update;
  if not found or inv.revoked_at is not null or inv.expires_at <= now() or inv.uses >= inv.max_uses then
    return 'invalid';
  end if;
  perform 1 from public.teams where id = inv.team_id for update;
  if exists (select 1 from public.team_members where team_id = inv.team_id and user_id = p_user) then
    if inv.kind = 'email' then
      update public.team_invites set uses = uses + 1 where id = p_invite;
    end if;
    return 'member';
  end if;
  if (select count(*) from public.team_members where user_id = p_user) >= p_max_teams then
    return 'limit';
  end if;
  select count(*) into taken from public.team_members where team_id = inv.team_id;
  if inv.kind = 'link' then
    taken := taken + (select count(*) from public.team_invites where team_id = inv.team_id and kind = 'email'
                      and revoked_at is null and uses < max_uses and expires_at > now());
  end if;
  if taken >= p_seats then
    return 'full';
  end if;
  insert into public.team_members (team_id, user_id, role, name, email) values (inv.team_id, p_user, inv.role, p_name, p_email);
  update public.team_invites set uses = uses + 1 where id = p_invite;
  return 'joined';
end
$$;

-- Ownership moves in one transaction: the old owner becomes an admin, the new one the owner.
create or replace function public.team_transfer(p_team uuid, p_from uuid, p_to uuid)
  returns boolean language plpgsql set search_path = ''
as $$
begin
  update public.teams set owner_id = p_to, updated_at = now() where id = p_team and owner_id = p_from;
  if not found then
    return false;
  end if;
  update public.team_members set role = 'admin' where team_id = p_team and user_id = p_from;
  update public.team_members set role = 'owner' where team_id = p_team and user_id = p_to;
  if not found then
    raise exception 'the new owner is not a member of this workspace';
  end if;
  return true;
end
$$;

revoke all on function public.team_join(uuid, uuid, text, text, integer, integer), public.team_transfer(uuid, uuid, uuid) from public, anon, authenticated;
grant execute on function public.team_join(uuid, uuid, text, text, integer, integer), public.team_transfer(uuid, uuid, uuid) to service_role;

alter table public.teams enable row level security;
alter table public.team_members enable row level security;
alter table public.team_invites enable row level security;
alter table public.team_runs enable row level security;
alter table public.team_findings enable row level security;
alter table public.team_messages enable row level security;
alter table public.team_events enable row level security;
revoke all on public.teams, public.team_members, public.team_invites, public.team_runs, public.team_findings, public.team_messages, public.team_events from anon, authenticated;

drop policy if exists "members read their teams" on public.teams;
create policy "members read their teams" on public.teams for select to authenticated using (public.is_team_member(id));
drop policy if exists "members read team members" on public.team_members;
create policy "members read team members" on public.team_members for select to authenticated using (public.is_team_member(team_id));
drop policy if exists "members read team runs" on public.team_runs;
create policy "members read team runs" on public.team_runs for select to authenticated using (public.is_team_member(team_id));
drop policy if exists "members read team findings" on public.team_findings;
create policy "members read team findings" on public.team_findings for select to authenticated using (public.is_team_member(team_id));
drop policy if exists "members read team messages" on public.team_messages;
create policy "members read team messages" on public.team_messages for select to authenticated using (public.is_team_member(team_id));
drop policy if exists "members read team events" on public.team_events;
create policy "members read team events" on public.team_events for select to authenticated using (public.is_team_member(team_id));
grant select on public.teams, public.team_members, public.team_runs, public.team_findings, public.team_messages, public.team_events to authenticated;

-- Members read the reports shared into their workspaces, and those reports' screenshots.
drop policy if exists "team members read shared runs" on public.runs;
create policy "team members read shared runs" on public.runs for select to authenticated using (public.shared_with_me(id));

drop policy if exists "team members read shared run evidence" on storage.objects;
create policy "team members read shared run evidence" on storage.objects
  for select to authenticated
  using (bucket_id = 'run-evidence' and public.shared_with_me(split_part(name, '/', 1)));

-- Live updates through Supabase Realtime (the publication exists on every Supabase project).
do $$
declare
  t text;
begin
  if exists (select 1 from pg_publication where pubname = 'supabase_realtime') then
    foreach t in array array['teams', 'team_members', 'team_runs', 'team_findings', 'team_messages', 'team_events'] loop
      if not exists (select 1 from pg_publication_tables where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = t) then
        execute format('alter publication supabase_realtime add table public.%I', t);
      end if;
    end loop;
  end if;
end
$$;

notify pgrst, 'reload schema';
