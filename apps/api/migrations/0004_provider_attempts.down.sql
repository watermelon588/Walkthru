-- Destructive: removes historical receipts. Export/reconcile pending attempts first.
drop function public.finish_provider_attempt(uuid,jsonb);
drop function public.begin_provider_attempt(uuid,jsonb);
drop table public.provider_attempts;
