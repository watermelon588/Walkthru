-- In-app live runs (docs/in-app-runner-plan.md). One row per test user asked to walk a site in the server's browser.
-- The table is both the queue the runner service claims from and the record the web page polls, because a `runs`
-- row only exists once the first page has been read. The API and the runner use the service role; browsers never
-- read this table directly.
create table public.cloud_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  group_id uuid not null,
  site text not null check (site ~ '^https?://' and char_length(site) <= 2000),
  goal text not null check (char_length(goal) between 1 and 500),
  persona text not null check (char_length(persona) between 1 and 60),
  max_steps integer not null check (max_steps between 1 and 100),
  status text not null default 'queued' check (status in ('queued', 'running', 'finished', 'failed', 'blocked', 'stopped')),
  run_id text,
  error text check (error is null or char_length(error) <= 300),
  lease uuid,
  locked_until timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index cloud_runs_queue on public.cloud_runs (created_at) where status in ('queued', 'running');
create index cloud_runs_group on public.cloud_runs (group_id);
create index cloud_runs_owner on public.cloud_runs (user_id, created_at desc);
alter table public.cloud_runs enable row level security;
revoke all on public.cloud_runs from anon, authenticated;

-- Claim the oldest queued test user, but only while fewer than p_limit browsers are running. The advisory lock makes
-- "count the running ones, then claim" one step, so two runner processes can never start a browser each past the limit.
-- A running row whose lease ran out belonged to a runner that died: it is closed as interrupted and never replayed,
-- because a half-finished journey must not repeat its clicks.
create function public.claim_cloud_run(p_lease_seconds integer, p_limit integer)
returns setof public.cloud_runs language plpgsql set search_path = public as $$
begin
  perform pg_advisory_xact_lock(hashtext('walkthru.cloud_runs'));
  update cloud_runs set status = 'failed', error = 'interrupted: the test browser stopped before finishing', lease = null,
                        locked_until = null, updated_at = now()
   where status = 'running' and locked_until < now();
  if (select count(*) from cloud_runs where status = 'running') >= p_limit then
    return;
  end if;
  return query
  update cloud_runs set status = 'running', lease = gen_random_uuid(),
                        locked_until = now() + make_interval(secs => p_lease_seconds), updated_at = now()
   where id = (select id from cloud_runs where status = 'queued' order by created_at limit 1 for update skip locked)
  returning *;
end $$;
revoke all on function public.claim_cloud_run(integer, integer) from public, anon, authenticated;
grant execute on function public.claim_cloud_run(integer, integer) to service_role;
