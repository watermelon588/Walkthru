-- Undo 0008: the evidence policy goes back to reading runs directly, then the functions go.
drop policy if exists "owners and public reports read run evidence" on storage.objects;
create policy "owners and public reports read run evidence" on storage.objects
  for select to anon, authenticated
  using (
    bucket_id = 'run-evidence'
    and exists (
      select 1 from public.runs
      where runs.id = split_part(name, '/', 1)
        and (runs.user_id = (select auth.uid()) or runs.public = true)
    )
  );

drop function if exists public.read_group_runs(uuid);
drop function if exists public.read_run(text);
drop function if exists public.run_evidence_readable(text);
