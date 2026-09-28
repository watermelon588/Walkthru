-- SD-6.5: service-only request claims. Unknown outcomes never expire into permission to execute again.
create table public.run_requests (
  user_id uuid not null references auth.users(id) on delete cascade,
  key uuid not null,
  operation text not null check (operation in ('start', 'observe', 'stop')),
  request_hash text not null check (request_hash ~ '^[a-f0-9]{64}$'),
  owner uuid not null,
  run_id uuid not null,
  state text not null default 'pending' check (state in ('pending', 'complete', 'uncertain', 'gone')),
  status integer check (status between 200 and 599),
  response jsonb,
  headers jsonb,
  created_at timestamptz not null default now(),
  finished_at timestamptz,
  primary key (user_id, key)
);
alter table public.run_requests enable row level security;
revoke all on public.run_requests from public, anon, authenticated, service_role;
create index run_requests_run_idx on public.run_requests(user_id, run_id);
create index run_requests_expiry_idx on public.run_requests(finished_at) where state = 'complete';

create function public.claim_run_request(p_user uuid, p_key uuid, p_operation text, p_hash text, p_owner uuid, p_run uuid)
returns jsonb language plpgsql security definer set search_path = public, pg_temp as $$
declare r public.run_requests;
begin
  -- Short per-account transaction lock serializes key admission and the per-run busy check across API instances.
  perform pg_advisory_xact_lock(hashtextextended(p_user::text, 6205));
  select * into r from public.run_requests where user_id = p_user and key = p_key for update;
  if found then
    if r.operation <> p_operation or r.request_hash <> p_hash or (p_operation <> 'start' and r.run_id <> p_run) then
      return jsonb_build_object('state', 'conflict');
    end if;
    if r.state = 'complete' and r.finished_at < now() - interval '24 hours' then
      update public.run_requests set state = 'gone', response = null, headers = null where user_id = p_user and key = p_key;
      r.state := 'gone';
    end if;
    if r.state = 'complete' then
      return jsonb_build_object('state', 'replay', 'status', r.status, 'response', r.response, 'headers', r.headers);
    end if;
    -- The DB HTTP layer may repeat an RPC after a lost response. Only the same server attempt owns this claim.
    if r.state = 'pending' and r.owner = p_owner then
      return jsonb_build_object('state', 'claimed', 'run_id', r.run_id);
    end if;
    return jsonb_build_object('state', r.state);
  end if;
  select * into r from public.run_requests where user_id = p_user and run_id = p_run and state in ('pending', 'uncertain') limit 1;
  if found then
    return jsonb_build_object('state', r.state);
  end if;
  insert into public.run_requests(user_id, key, operation, request_hash, owner, run_id)
    values (p_user, p_key, p_operation, p_hash, p_owner, p_run);
  return jsonb_build_object('state', 'claimed', 'run_id', p_run);
end $$;

create function public.finish_run_request(p_user uuid, p_key uuid, p_owner uuid, p_state text, p_status integer, p_response jsonb, p_headers jsonb)
returns boolean language plpgsql security definer set search_path = public, pg_temp as $$
begin
  if p_state not in ('complete', 'uncertain') then raise exception 'Invalid request completion state'; end if;
  update public.run_requests set state = p_state, status = p_status, response = p_response, headers = p_headers, finished_at = now()
    where user_id = p_user and key = p_key and owner = p_owner and state = 'pending';
  if found then return true; end if;
  -- A repeated completion RPC may confirm its own write but cannot replace it or resurrect a deleted response.
  return exists(select 1 from public.run_requests where user_id = p_user and key = p_key and owner = p_owner
    and state = p_state and status = p_status and response is not distinct from p_response and headers is not distinct from p_headers);
end $$;

create function public.expire_run_requests() returns void language sql security definer set search_path = public, pg_temp as $$
  update public.run_requests set state = 'gone', response = null, headers = null
    where state = 'complete' and finished_at < now() - interval '24 hours';
$$;

create function public.erase_run_request_responses() returns trigger language plpgsql security definer set search_path = public, pg_temp as $$
begin
  update public.run_requests set state = 'gone', response = null, headers = null
    where user_id = old.user_id and replace(run_id::text, '-', '') = replace(old.id, '-', '');
  return old;
end $$;
create trigger erase_run_request_responses before delete on public.runs for each row execute function public.erase_run_request_responses();

revoke all on function public.claim_run_request(uuid, uuid, text, text, uuid, uuid) from public, anon, authenticated;
revoke all on function public.finish_run_request(uuid, uuid, uuid, text, integer, jsonb, jsonb) from public, anon, authenticated;
revoke all on function public.expire_run_requests() from public, anon, authenticated;
revoke all on function public.erase_run_request_responses() from public, anon, authenticated, service_role;
grant execute on function public.claim_run_request(uuid, uuid, text, text, uuid, uuid) to service_role;
grant execute on function public.finish_run_request(uuid, uuid, uuid, text, integer, jsonb, jsonb) to service_role;
grant execute on function public.expire_run_requests() to service_role;
-- No automatic down migration: dropping tombstones would allow delayed retries to execute again.
