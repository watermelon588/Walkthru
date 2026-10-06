-- Rolling back deletes reservation history and the funded budget configuration.
drop function if exists public.refund_reservation(uuid, text, text);
drop function if exists public.finish_reservation(uuid, jsonb);
drop function if exists public.mark_reservation_dispatched(uuid);
drop function if exists public.reserve_run(uuid, text, timestamptz, timestamptz, integer, bigint, text);
drop function if exists public.reservation_liability(timestamptz);
drop table if exists public.spend_budgets;
drop table if exists public.run_reservations;
