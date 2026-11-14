-- Migration 0008: shared reports open by link only, step 1 of 2 (additive, safe before the web deploy).
-- "anyone reads public runs" let anyone holding the public key LIST every shared report (site, goal, owner id, report).
-- Browsers now read one run, or one Plus group, through these functions. 0009 then drops that policy; apply it only
-- after the web build that calls read_run / read_group_runs is live, or shared links break.

-- One run the viewer may open: shared by link, their own, or shared with their team. Only the columns the web shows.
create or replace function public.read_run(p_id text) returns jsonb
  language sql stable security definer set search_path = ''
  as $$
    select jsonb_build_object('id', r.id, 'site', r.site, 'goal', r.goal, 'persona', r.persona, 'kind', r.kind,
                              'status', r.status, 'steps', r.steps, 'report', r.report, 'public', r.public,
                              'created_at', r.created_at, 'updated_at', r.updated_at,
                              'evidence_purged_at', r.evidence_purged_at, 'group_id', r.group_id)
    from public.runs r
    where r.id = p_id and (r.public or r.user_id = (select auth.uid()) or public.shared_with_me(r.id))
  $$;

-- The readable runs of one Plus group (several test users, one goal), oldest first.
create or replace function public.read_group_runs(p_group uuid) returns setof jsonb
  language sql stable security definer set search_path = ''
  as $$
    select v from public.runs r, lateral (select public.read_run(r.id) as v) x
    where r.group_id = p_group and x.v is not null
    order by r.created_at limit 10
  $$;

-- Screenshots of a run the viewer owns or that is shared by link. Storage policies run as the viewer, and after 0009
-- anonymous viewers may not touch public.runs at all (even a subquery fails), so the policy calls this instead.
create or replace function public.run_evidence_readable(p_id text) returns boolean
  language sql stable security definer set search_path = ''
  as $$ select exists (select 1 from public.runs where id = p_id and (public or user_id = (select auth.uid()))) $$;

revoke all on function public.read_run(text), public.read_group_runs(uuid), public.run_evidence_readable(text) from public;
grant execute on function public.read_run(text), public.read_group_runs(uuid), public.run_evidence_readable(text) to anon, authenticated;

drop policy if exists "owners and public reports read run evidence" on storage.objects;
create policy "owners and public reports read run evidence" on storage.objects
  for select to anon, authenticated
  using (
    bucket_id = 'run-evidence'
    and public.run_evidence_readable(split_part(name, '/', 1))
  );
