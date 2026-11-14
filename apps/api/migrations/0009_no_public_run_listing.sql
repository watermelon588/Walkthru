-- Migration 0009: shared reports open by link only, step 2 of 2. Apply AFTER the web build that reads runs through
-- read_run / read_group_runs (0008) is deployed. Neither anonymous nor signed-in visitors can list shared reports any
-- more; owners ("owner reads runs") and team members ("team members read shared runs") keep their own policies.
drop policy if exists "anyone reads public runs" on public.runs;
revoke select on public.runs from anon;
