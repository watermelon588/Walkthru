-- R-S9 proposed additive storage: every model/data entry point (journey runs, Instant Scans, owner/MCP scans and checks,
-- comparisons, watch checks, AI answer batches, Scout answers) reserves in the one R-S8 ledger before dispatch.
-- Each operation has its own allowance per owner and window; all of them share the funded platform budget.
-- Activation (applying this, setting RESERVATIONS=postgres, funding budgets) is separate from building/testing it.

alter table public.run_reservations
  add column operation text not null default 'run'
    check (operation in ('run', 'public_scan', 'scan', 'watch', 'citations', 'scout'));
-- One run credit per journey reservation; other operations reserve several units at once (a comparison of 4 sites).
alter table public.run_reservations drop constraint run_reservations_units_check;
alter table public.run_reservations add constraint run_reservations_units_check
  check (units between 1 and 1000 and (operation <> 'run' or units = 1));
create index run_reservations_owner_operation_idx on public.run_reservations (user_id, operation, window_start, state);

-- p_owner is the account, the workspace (Scout) or the all-zero UUID for anonymous Instant Scans.
-- Allowance counts units in use for (owner, operation, exact window): open reservations plus settled work that used its
-- credit. A replay of a released (never dispatched) key is re-admitted under the same checks; other replays return
-- the existing reservation and its state, so the caller never executes settled work twice.
create function public.reserve_work(p_owner uuid, p_operation text, p_key text, p_window_start timestamptz,
                                    p_window_end timestamptz, p_allowed integer, p_units integer, p_max_cost bigint,
                                    p_price_version text)
returns jsonb language plpgsql security definer set search_path = public, pg_temp as $$
declare existing public.run_reservations; used integer; budget record; new_id uuid; since timestamptz;
begin
  if p_owner is null or p_operation not in ('run', 'public_scan', 'scan', 'watch', 'citations', 'scout')
     or p_key !~ '^[A-Za-z0-9:_-]{1,200}$' or p_window_start is null or p_window_end <= p_window_start
     or p_allowed is null or p_allowed < 0 or p_units is null or p_units not between 1 and 1000
     or (p_operation = 'run' and p_units <> 1) or p_max_cost is null or p_max_cost not between 0 and 1000000000000
     or p_price_version !~ '^[a-z0-9.-]{1,64}$' then
    raise exception 'Invalid reservation request';
  end if;
  -- One admission at a time per owner, then platform-wide through the budget rows (V1 volume; simple and exact).
  perform pg_advisory_xact_lock(hashtextextended('run_reservation:' || p_owner::text, 0));
  select * into existing from public.run_reservations where user_id = p_owner and operation_key = p_key;
  if found then
    if existing.operation <> p_operation or existing.window_start <> p_window_start or existing.window_end <> p_window_end
       or existing.units <> p_units or existing.max_cost_microusd <> p_max_cost or existing.price_version <> p_price_version then
      return jsonb_build_object('status', 'conflict', 'id', existing.id);
    end if;
    if existing.state <> 'released' then
      return jsonb_build_object('status', 'replayed', 'id', existing.id, 'state', existing.state);
    end if;
  end if;
  perform 1 from public.spend_budgets for update;
  if (select count(*) from public.spend_budgets) < 2 then
    return jsonb_build_object('status', 'unfunded');
  end if;
  select coalesce(sum(units), 0) into used from public.run_reservations
   where user_id = p_owner and operation = p_operation and window_start = p_window_start and window_end = p_window_end
     and (state = 'reserved' or (state = 'settled' and outcome->>'credit' = '1'));
  if used + p_units > p_allowed then
    return jsonb_build_object('status', 'no_credits', 'used', used);
  end if;
  for budget in select key, limit_microusd from public.spend_budgets loop
    since := case budget.key when 'platform_daily' then date_trunc('day', now() at time zone 'utc') at time zone 'utc'
                             else date_trunc('month', now() at time zone 'utc') at time zone 'utc' end;
    if public.reservation_liability(since) + p_max_cost > budget.limit_microusd then
      return jsonb_build_object('status', 'budget', 'budget', budget.key);
    end if;
  end loop;
  if existing.id is not null then  -- re-admit a released key: nothing was spent under it
    update public.run_reservations set state = 'reserved', outcome = null, actual_cost_microusd = null, updated_at = now()
     where id = existing.id returning id into new_id;
  else
    insert into public.run_reservations(user_id, operation, operation_key, window_start, window_end, units, max_cost_microusd, price_version)
    values (p_owner, p_operation, p_key, p_window_start, p_window_end, p_units, p_max_cost, p_price_version) returning id into new_id;
  end if;
  return jsonb_build_object('status', 'reserved', 'id', new_id, 'used', used + p_units);
end $$;

-- R-S8's journey-run entry point is now the 'run' operation of the shared admission. Its replay keeps the R-S8 answer
-- (the existing reservation) for released keys too, so a request replay never re-admits a journey run.
create or replace function public.reserve_run(p_user uuid, p_key text, p_window_start timestamptz, p_window_end timestamptz,
                                              p_allowed integer, p_max_cost bigint, p_price_version text)
returns jsonb language plpgsql security definer set search_path = public, pg_temp as $$
declare existing public.run_reservations;
begin
  select * into existing from public.run_reservations where user_id = p_user and operation_key = p_key;
  if found and existing.state = 'released' and existing.operation = 'run' then
    return jsonb_build_object('status', 'replayed', 'id', existing.id, 'state', existing.state);
  end if;
  return public.reserve_work(p_user, 'run', p_key, p_window_start, p_window_end, p_allowed, 1, p_max_cost, p_price_version);
end $$;

revoke all on function public.reserve_work(uuid, text, text, timestamptz, timestamptz, integer, integer, bigint, text)
  from public, anon, authenticated;
grant execute on function public.reserve_work(uuid, text, text, timestamptz, timestamptz, integer, integer, bigint, text) to service_role;
