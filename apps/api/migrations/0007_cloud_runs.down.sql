-- Undo 0007: queued and finished live-run records are deleted; the journeys' own `runs` rows and reports stay.
drop function public.claim_cloud_run(integer, integer);
drop table public.cloud_runs;
