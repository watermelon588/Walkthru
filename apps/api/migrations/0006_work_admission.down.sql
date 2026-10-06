-- Undo 0006: non-run reservations are deleted (rollback deletes history, as in 0005), then R-S8's reserve_run returns.
drop function public.reserve_work(uuid, text, text, timestamptz, timestamptz, integer, integer, bigint, text);
delete from public.run_reservations where operation <> 'run';
drop index public.run_reservations_owner_operation_idx;
alter table public.run_reservations drop constraint run_reservations_units_check;
alter table public.run_reservations add constraint run_reservations_units_check check (units = 1);
alter table public.run_reservations drop column operation;
create or replace function public.reserve_run(p_user uuid, p_key text, p_window_start timestamptz, p_window_end timestamptz,
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
