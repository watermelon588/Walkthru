-- Undo 0009: anyone may read (and list) runs marked public again.
grant select on public.runs to anon;
drop policy if exists "anyone reads public runs" on public.runs;
create policy "anyone reads public runs" on public.runs
  for select to anon, authenticated
  using (public = true);
