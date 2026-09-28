-- SD-6.2. LangGraph checkpoint-postgres 3.1.2, migrations 0..9 (MIT, THIRD_PARTY.md).
-- Pause all API/worker processes first: existing public checkpoint tables move atomically.
-- Indexes are deliberately non-concurrent because the migration runner uses one transaction.
create schema if not exists walkthru_checkpoints;
revoke all on schema walkthru_checkpoints from public;

do $$
declare t text;
begin
  foreach t in array array['checkpoint_migrations', 'checkpoints', 'checkpoint_blobs', 'checkpoint_writes'] loop
    if to_regclass('public.' || t) is not null then
      if to_regclass('walkthru_checkpoints.' || t) is not null then
        raise exception 'Checkpoint tables exist in both schemas; reconcile before migrating';
      end if;
      execute format('alter table public.%I set schema walkthru_checkpoints', t);
    end if;
  end loop;
end $$;

create table if not exists walkthru_checkpoints.checkpoint_migrations (v integer primary key);
do $$
begin
  if exists(select 1 from walkthru_checkpoints.checkpoint_migrations where v > 9) then
    raise exception 'Checkpoint schema is newer than the pinned library';
  end if;
end $$;
create table if not exists walkthru_checkpoints.checkpoints (
  thread_id text not null, checkpoint_ns text not null default '', checkpoint_id text not null,
  parent_checkpoint_id text, type text, checkpoint jsonb not null, metadata jsonb not null default '{}',
  primary key (thread_id, checkpoint_ns, checkpoint_id)
);
create table if not exists walkthru_checkpoints.checkpoint_blobs (
  thread_id text not null, checkpoint_ns text not null default '', channel text not null,
  version text not null, type text not null, blob bytea,
  primary key (thread_id, checkpoint_ns, channel, version)
);
alter table walkthru_checkpoints.checkpoint_blobs alter column blob drop not null;
create table if not exists walkthru_checkpoints.checkpoint_writes (
  thread_id text not null, checkpoint_ns text not null default '', checkpoint_id text not null,
  task_id text not null, idx integer not null, channel text not null, type text, blob bytea not null,
  task_path text not null default '',
  primary key (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);
alter table walkthru_checkpoints.checkpoint_writes add column if not exists task_path text not null default '';
create index if not exists checkpoints_thread_id_idx on walkthru_checkpoints.checkpoints(thread_id);
create index if not exists checkpoint_blobs_thread_id_idx on walkthru_checkpoints.checkpoint_blobs(thread_id);
create index if not exists checkpoint_writes_thread_id_idx on walkthru_checkpoints.checkpoint_writes(thread_id);
insert into walkthru_checkpoints.checkpoint_migrations(v) select generate_series(0, 9) on conflict do nothing;

-- Moving a legacy table preserves its old grants. Remove them explicitly, including default grants.
revoke all on all tables in schema walkthru_checkpoints from public;
do $$
declare r text;
begin
  foreach r in array array['anon', 'authenticated', 'service_role'] loop
    if exists(select 1 from pg_roles where rolname = r) then
      execute format('revoke all on schema walkthru_checkpoints from %I', r);
      execute format('revoke all on all tables in schema walkthru_checkpoints from %I', r);
    end if;
  end loop;
end $$;
-- Forward-only: moving private customer snapshots back into a REST-exposed schema is not a safe rollback.
