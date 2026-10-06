-- R-S7 proposed additive storage. Activation is separate from building/testing it.
-- No customer charge, balance, provider admission, or lease-based release.
create table public.provider_attempts (
  id uuid primary key,
  identity jsonb not null,
  state text not null default 'pending' check (state in ('pending', 'succeeded', 'failed', 'skipped')),
  result jsonb,
  created_at timestamptz not null default now(),
  finished_at timestamptz,
  check ((state = 'pending' and result is null and finished_at is null)
      or (state <> 'pending' and result is not null and finished_at is not null))
);
alter table public.provider_attempts enable row level security;
revoke all on public.provider_attempts from public, anon, authenticated, service_role;
grant select on public.provider_attempts to service_role;
create index provider_attempts_operation_idx on public.provider_attempts ((identity->>'operation_id'), created_at, id);
create index provider_attempts_run_idx on public.provider_attempts ((identity->>'run_id'), created_at, id);
create index provider_attempts_pending_idx on public.provider_attempts (created_at) where state = 'pending';

create function public.begin_provider_attempt(p_id uuid, p_identity jsonb)
returns boolean language plpgsql security definer set search_path = public, pg_temp as $$
declare key text; value jsonb; old_identity jsonb;
begin
  if p_id is null or jsonb_typeof(p_identity) is distinct from 'object'
     or not p_identity ?& array['operation_id','stage_id','stage','attempt_number','provider','model'] then
    raise exception 'Invalid provider identity';
  end if;
  for key, value in select * from jsonb_each(p_identity) loop
    if key in ('operation_id','stage_id','run_id','user_id','job_lease_id','request_id') then
      if value <> 'null'::jsonb then perform (value #>> '{}')::uuid; end if;
    elsif key in ('attempt_number','job_attempt','job_id') then
      if value <> 'null'::jsonb and (jsonb_typeof(value) <> 'number' or value::text !~ '^[0-9]+$'
          or value::text::numeric not between 1 and 1000000000000000) then raise exception 'Invalid attempt number'; end if;
    elsif key = 'provider' then
      if value #>> '{}' not in ('groq','gemini','openrouter','anthropic','claude_vertex','typesafe') then raise exception 'Invalid provider'; end if;
    elsif key = 'stage' then
      if value #>> '{}' not in ('goal_plan','persona_decision','first_impression','synthesis','citation_web','citation_memory','scout','other') then raise exception 'Invalid stage'; end if;
    elsif key = 'model' then
      if jsonb_typeof(value) <> 'string' or value #>> '{}' !~ '^[a-zA-Z0-9_./:@-]{1,128}$' then raise exception 'Invalid model'; end if;
    else raise exception 'Unexpected provider identity field'; end if;
  end loop;
  if p_identity->>'operation_id' is null or p_identity->>'stage_id' is null or p_identity->>'attempt_number' is null
     or p_identity->>'stage' is null or p_identity->>'model' is null or p_identity->>'provider' is null then
    raise exception 'Missing provider identity';
  end if;
  insert into public.provider_attempts(id, identity) values(p_id, p_identity) on conflict (id) do nothing;
  select identity into old_identity from public.provider_attempts where id = p_id;
  return old_identity = p_identity;
end $$;

create function public.finish_provider_attempt(p_id uuid, p_result jsonb)
returns boolean language plpgsql security definer set search_path = public, pg_temp as $$
declare key text; value jsonb; old_result jsonb;
begin
  if jsonb_typeof(p_result) is distinct from 'object' or not p_result ?& array['state','error_kind','duration_ms','usage','estimate','provider_request_id_hash']
     or p_result->>'state' is null or p_result->>'state' not in ('succeeded','failed','skipped')
     or jsonb_typeof(p_result->'usage') is distinct from 'object' or jsonb_typeof(p_result->'estimate') is distinct from 'object'
     or not (p_result->'usage') ?& array['input_tokens','output_tokens','total_tokens','cache_read_tokens','cache_write_tokens','cache_write_5m_tokens','cache_write_1h_tokens',
        'cache_storage_token_seconds','reasoning_tokens','image_input_tokens','image_output_tokens','audio_input_tokens','audio_output_tokens','tool_input_tokens','tool_requests',
        'reported_cost_microunits','reported_tool_cost_microusd','cost_currency','input_semantics','output_semantics','usage_source']
     or not (p_result->'estimate') ?& array['price_version','currency','source_date','basis','token_estimate_microusd','input_rate_microusd_per_million','output_rate_microusd_per_million','total_cost_microusd'] then
    raise exception 'Invalid provider result';
  end if;
  for key in select jsonb_object_keys(p_result) loop
    if key not in ('state','error_kind','duration_ms','usage','estimate','provider_request_id_hash') then raise exception 'Unexpected provider result field'; end if;
  end loop;
  if p_result->>'error_kind' is not null and p_result->>'error_kind' not in ('timeout','http','transport','parse','abstained','error','cancelled','circuit_open') then
    raise exception 'Invalid provider error';
  end if;
  if p_result->>'provider_request_id_hash' is not null and p_result->>'provider_request_id_hash' !~ '^[a-f0-9]{64}$' then raise exception 'Invalid provider request hash'; end if;
  if jsonb_typeof(p_result->'duration_ms') is distinct from 'number' or p_result->>'duration_ms' !~ '^[0-9]+$'
     or (p_result->>'duration_ms')::numeric > 1000000000000000 then raise exception 'Invalid duration'; end if;
  for key, value in select * from jsonb_each(p_result->'usage') loop
    if key = 'input_semantics' then
      if jsonb_typeof(value) <> 'string' or value #>> '{}' not in ('unknown','inclusive','excludes_cache') then raise exception 'Invalid input semantics'; end if;
    elsif key = 'output_semantics' then
      if jsonb_typeof(value) <> 'string' or value #>> '{}' not in ('unknown','inclusive','excludes_reasoning') then raise exception 'Invalid output semantics'; end if;
    elsif key = 'usage_source' then
      if jsonb_typeof(value) <> 'string' or value #>> '{}' not in ('langchain','gemini','anthropic','typesafe','openai','openrouter') then raise exception 'Invalid usage source'; end if;
    elsif key = 'cost_currency' then
      if value <> 'null'::jsonb and value #>> '{}' <> 'openrouter_credits' then raise exception 'Invalid reported currency'; end if;
    elsif key in ('input_tokens','output_tokens','total_tokens','cache_read_tokens','cache_write_tokens','cache_write_5m_tokens','cache_write_1h_tokens',
                  'cache_storage_token_seconds','reasoning_tokens','image_input_tokens','image_output_tokens','audio_input_tokens','audio_output_tokens',
                  'tool_input_tokens','tool_requests','reported_cost_microunits','reported_tool_cost_microusd') then
      if value <> 'null'::jsonb and (jsonb_typeof(value) <> 'number' or value::text !~ '^[0-9]+$'
          or value::text::numeric > 1000000000000000) then raise exception 'Invalid provider usage'; end if;
    else raise exception 'Unexpected provider usage field'; end if;
  end loop;
  -- Estimates have one fixed catalog; they are partial token baselines, never billed totals.
  for key, value in select * from jsonb_each(p_result->'estimate') loop
    if key = 'price_version' then
      if value <> 'null'::jsonb and value #>> '{}' <> 'groq-standard-2026-10-06' then raise exception 'Invalid price version'; end if;
    elsif key = 'source_date' then
      if value <> 'null'::jsonb and value #>> '{}' <> '2026-10-06' then raise exception 'Invalid price date'; end if;
    elsif key = 'currency' then
      if value #>> '{}' <> 'USD' then raise exception 'Invalid estimate currency'; end if;
    elsif key = 'basis' then
      if value #>> '{}' not in ('standard_tokens_no_cache_discount','unpriced') then raise exception 'Invalid estimate basis'; end if;
    elsif key = 'total_cost_microusd' then
      if value <> 'null'::jsonb then raise exception 'Total cost is unknown'; end if;
    elsif key in ('token_estimate_microusd','input_rate_microusd_per_million','output_rate_microusd_per_million') then
      if value <> 'null'::jsonb and (jsonb_typeof(value) <> 'number' or value::text !~ '^[0-9]+$'
          or value::text::numeric > 1000000000000000) then raise exception 'Invalid estimate amount'; end if;
    else raise exception 'Unexpected estimate field'; end if;
  end loop;
  update public.provider_attempts set result = p_result, state = p_result->>'state', finished_at = now() where id = p_id and state = 'pending';
  if found then return true; end if;
  select result into old_result from public.provider_attempts where id = p_id;
  return coalesce(old_result = p_result, false);
end $$;

revoke all on function public.begin_provider_attempt(uuid,jsonb), public.finish_provider_attempt(uuid,jsonb) from public, anon, authenticated;
grant execute on function public.begin_provider_attempt(uuid,jsonb), public.finish_provider_attempt(uuid,jsonb) to service_role;
