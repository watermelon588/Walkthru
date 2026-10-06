-- R-S8 proposed additive storage: atomic run-credit and provider-budget reservations with an explicit state machine.
-- Activation (applying this, setting RESERVATIONS=postgres, funding budgets) is separate from building/testing it.
-- Money is integer micro-USD. Nothing here charges a customer, changes a price or creates a grant.

create table public.run_reservations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  operation_key text not null check (operation_key ~ '^[A-Za-z0-9:_-]{1,200}$'),  -- accepted request/run id
  window_start timestamptz not null,
  window_end timestamptz not null check (window_end > window_start),           -- the plan or pass counting window
  units integer not null default 1 check (units = 1),                          -- one test run credit per reservation
  max_cost_microusd bigint not null check (max_cost_microusd between 0 and 1000000000000),
  price_version text not null check (price_version ~ '^[a-z0-9.-]{1,64}$'),
  state text not null default 'reserved' check (state in ('reserved', 'settled', 'released', 'refunded')),
  dispatched boolean not null default false,  -- provider work may have started; such a reservation can never be released
  actual_cost_microusd bigint check (actual_cost_microusd between 0 and 1000000000000),  -- null = unknown, counted at max
  outcome jsonb,                              -- the terminal payload, for exact idempotent replay
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, operation_key),
  check ((state = 'reserved') = (outcome is null)),
  check (state <> 'released' or not dispatched)
);
alter table public.run_reservations enable row level security;
revoke all on public.run_reservations from public, anon, authenticated, service_role;
grant select on public.run_reservations to service_role;
create index run_reservations_user_window_idx on public.run_reservations (user_id, window_start, state);
create index run_reservations_created_idx on public.run_reservations (created_at);
create index run_reservations_open_idx on public.run_reservations (created_at) where state = 'reserved';

-- The funded platform provider budget. No row means not funded: reservations fail closed.
create table public.spend_budgets (
  key text primary key check (key in ('platform_daily', 'platform_monthly')),
  limit_microusd bigint not null check (limit_microusd between 0 and 1000000000000),
  updated_at timestamptz not null default now()
);
alter table public.spend_budgets enable row level security;
revoke all on public.spend_budgets from public, anon, authenticated, service_role;
grant select on public.spend_budgets to service_role;

-- Provider liability of reservations created since p_since: open, settled and refunded work counts its actual cost,
-- or its reserved maximum while the actual cost is unknown. Released (never dispatched) work counts nothing.
create function public.reservation_liability(p_since timestamptz)
returns bigint language sql stable security definer set search_path = public, pg_temp as $$
  select coalesce(sum(case when state = 'released' then 0 else coalesce(actual_cost_microusd, max_cost_microusd) end), 0)::bigint
  from public.run_reservations where created_at >= p_since
$$;

create function public.reserve_run(p_user uuid, p_key text, p_window_start timestamptz, p_window_end timestamptz,
                                   p_allowed integer, p_max_cost bigint, p_price_version text)
returns jsonb language plpgsql security definer set search_path = public, pg_temp as $$
declare existing public.run_reservations; used integer; budget record; new_id uuid; since timestamptz;
begin
  if p_user is null or p_key !~ '^[A-Za-z0-9:_-]{1,200}$' or p_window_start is null or p_window_end <= p_window_start
     or p_allowed is null or p_allowed < 0 or p_max_cost is null or p_max_cost not between 0 and 1000000000000
     or p_price_version !~ '^[a-z0-9.-]{1,64}$' then
    raise exception 'Invalid reservation request';
  end if;
  -- One admission at a time per user, then platform-wide through the budget rows (V1 volume; simple and exact).
  perform pg_advisory_xact_lock(hashtextextended('run_reservation:' || p_user::text, 0));
  select * into existing from public.run_reservations where user_id = p_user and operation_key = p_key;
  if found then
    if existing.window_start <> p_window_start or existing.window_end <> p_window_end or existing.max_cost_microusd <> p_max_cost
       or existing.price_version <> p_price_version then
      return jsonb_build_object('status', 'conflict', 'id', existing.id);
    end if;
    return jsonb_build_object('status', 'replayed', 'id', existing.id, 'state', existing.state);
  end if;
  perform 1 from public.spend_budgets for update;
  if (select count(*) from public.spend_budgets) < 2 then
    return jsonb_build_object('status', 'unfunded');
  end if;
  -- Credits in use: open reservations and settled runs that consumed their credit. Released, refunded and
  -- credit-free settlements (refused goals, start failures) give the credit back.
  select count(*) into used from public.run_reservations
   where user_id = p_user and window_start = p_window_start and window_end = p_window_end
     and (state = 'reserved' or (state = 'settled' and outcome->>'credit' = '1'));
  if used >= p_allowed then
    return jsonb_build_object('status', 'no_credits', 'used', used);
  end if;
  for budget in select key, limit_microusd from public.spend_budgets loop
    since := case budget.key when 'platform_daily' then date_trunc('day', now() at time zone 'utc') at time zone 'utc'
                             else date_trunc('month', now() at time zone 'utc') at time zone 'utc' end;
    if public.reservation_liability(since) + p_max_cost > budget.limit_microusd then
      return jsonb_build_object('status', 'budget', 'budget', budget.key);
    end if;
  end loop;
  insert into public.run_reservations(user_id, operation_key, window_start, window_end, max_cost_microusd, price_version)
  values (p_user, p_key, p_window_start, p_window_end, p_max_cost, p_price_version) returning id into new_id;
  return jsonb_build_object('status', 'reserved', 'id', new_id, 'used', used + 1);
end $$;

-- Provider work is about to start (or may have started). From now on the reservation can only be settled.
create function public.mark_reservation_dispatched(p_id uuid)
returns boolean language plpgsql security definer set search_path = public, pg_temp as $$
begin
  update public.run_reservations set dispatched = true, updated_at = now() where id = p_id and state = 'reserved';
  if found then return true; end if;
  return exists (select 1 from public.run_reservations where id = p_id and state <> 'released');  -- late or repeated mark
end $$;

-- Terminal outcome: {"state":"settled","actual_cost_microusd":int|null,"reason":...,"credit":0|1}
--                or {"state":"released","actual_cost_microusd":0,"reason":"not_dispatched","credit":0}.
-- `credit` says whether the customer's run credit was used; provider cost is counted separately either way.
-- Identical replays return true; conflicting or impossible transitions return false. No time-based release exists.
create function public.finish_reservation(p_id uuid, p_outcome jsonb)
returns boolean language plpgsql security definer set search_path = public, pg_temp as $$
declare r public.run_reservations; cost jsonb;
begin
  if jsonb_typeof(p_outcome) is distinct from 'object' or (select count(*) from jsonb_object_keys(p_outcome)) <> 4
     or not p_outcome ?& array['state', 'actual_cost_microusd', 'reason', 'credit'] or p_outcome->'credit' not in ('0'::jsonb, '1'::jsonb) then
    raise exception 'Invalid reservation outcome';
  end if;
  cost := p_outcome->'actual_cost_microusd';
  if cost <> 'null'::jsonb and (jsonb_typeof(cost) <> 'number' or cost::text !~ '^[0-9]+$' or cost::text::numeric > 1000000000000) then
    raise exception 'Invalid reservation cost';
  end if;
  if not ((p_outcome->>'state' = 'settled' and p_outcome->>'reason' in ('completed', 'stopped', 'failed', 'refused', 'reconciled'))
          or (p_outcome->>'state' = 'released' and p_outcome->>'reason' = 'not_dispatched' and cost = '0'::jsonb and p_outcome->'credit' = '0'::jsonb)) then
    raise exception 'Invalid reservation outcome';
  end if;
  select * into r from public.run_reservations where id = p_id for update;
  if not found then return false; end if;
  if r.state <> 'reserved' then return r.outcome = p_outcome; end if;
  if p_outcome->>'state' = 'released' and r.dispatched then return false; end if;
  update public.run_reservations
     set state = p_outcome->>'state', outcome = p_outcome, updated_at = now(),
         actual_cost_microusd = case when cost = 'null'::jsonb then null else cost::text::bigint end
   where id = p_id;
  return true;
end $$;

-- A founder-owned refund returns the run credit to the customer. Provider liability stays counted: it was spent.
create function public.refund_reservation(p_id uuid, p_actor text, p_reason text)
returns boolean language plpgsql security definer set search_path = public, pg_temp as $$
declare r public.run_reservations; refund jsonb;
begin
  if p_actor is distinct from 'founder' or p_reason is null or length(p_reason) not between 1 and 300 then
    raise exception 'Invalid refund';
  end if;
  select * into r from public.run_reservations where id = p_id for update;
  if not found then return false; end if;
  refund := jsonb_build_object('actor', p_actor, 'reason', p_reason);
  if r.state = 'refunded' then return r.outcome->'refund' = refund; end if;
  if r.state <> 'settled' or r.outcome->'credit' <> '1'::jsonb then return false; end if;
  update public.run_reservations set state = 'refunded', outcome = r.outcome || jsonb_build_object('refund', refund), updated_at = now() where id = p_id;
  return true;
end $$;

revoke all on function public.reservation_liability(timestamptz), public.reserve_run(uuid, text, timestamptz, timestamptz, integer, bigint, text),
  public.mark_reservation_dispatched(uuid), public.finish_reservation(uuid, jsonb), public.refund_reservation(uuid, text, text)
  from public, anon, authenticated;
grant execute on function public.reserve_run(uuid, text, timestamptz, timestamptz, integer, bigint, text),
  public.mark_reservation_dispatched(uuid), public.finish_reservation(uuid, jsonb) to service_role;
-- refund_reservation stays owner-only (the founder runs it from SQL or the local admin); service_role cannot refund.
-- Revoked from service_role explicitly: Supabase default privileges grant it execute on new functions.
revoke all on function public.refund_reservation(uuid, text, text), public.reservation_liability(timestamptz) from service_role;
