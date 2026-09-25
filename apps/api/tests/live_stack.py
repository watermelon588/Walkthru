"""A throwaway Postgres + PostgREST with Supabase's roles, for tests that must prove row-level security for real.

Needs the Postgres server binaries (initdb, pg_ctl) and a PostgREST binary. Set PG_BIN (a directory) and
POSTGREST_BIN (the executable), or have them on PATH / in /usr/lib/postgresql/*/bin. Tests skip when they are
missing, so the rest of the suite still runs anywhere. Never points at a real Supabase project.
"""

import base64
import glob
import hashlib
import hmac
import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
from contextlib import contextmanager

import httpx

SECRET = "walkthru-local-test-secret-at-least-32-chars"

# The pieces of a Supabase project that schema.sql relies on: roles, auth.users, auth.uid(), storage tables,
# default grants to the API roles, and the realtime publication.
SUPABASE_STUB = """
create role anon nologin noinherit;
create role authenticated nologin noinherit;
create role service_role nologin noinherit bypassrls;
create role authenticator login noinherit;
grant anon, authenticated, service_role to authenticator;
create schema auth;
create table auth.users (id uuid primary key, email text, email_confirmed_at timestamptz, raw_user_meta_data jsonb not null default '{}');
create function auth.uid() returns uuid language sql stable
  as $$ select nullif(current_setting('request.jwt.claims', true)::json->>'sub', '')::uuid $$;
grant usage on schema auth to anon, authenticated, service_role;
grant execute on function auth.uid() to anon, authenticated, service_role;
create schema storage;
create table storage.buckets (id text primary key, name text, public boolean, file_size_limit bigint, allowed_mime_types text[]);
create table storage.objects (id uuid primary key default gen_random_uuid(), bucket_id text, name text, owner uuid);
alter table storage.objects enable row level security;
grant usage on schema storage to anon, authenticated, service_role;
grant select on storage.objects to anon, authenticated;
grant all on all tables in schema storage to service_role;
grant usage on schema public to anon, authenticated, service_role;
alter default privileges in schema public grant all on tables to anon, authenticated, service_role;
alter default privileges in schema public grant all on functions to anon, authenticated, service_role;
alter default privileges in schema public grant all on sequences to anon, authenticated, service_role;
create publication supabase_realtime;
"""


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def jwt(claims: dict) -> str:
    """HS256 token PostgREST accepts, like a Supabase access token (role authenticated) or the secret key (service_role)."""
    head = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = _b64(json.dumps({"exp": int(time.time()) + 3600, **claims}).encode())
    sig = _b64(hmac.new(SECRET.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest())
    return f"{head}.{body}.{sig}"


def binaries() -> tuple[str, str] | None:
    pg = os.environ.get("PG_BIN") or next(iter(sorted(glob.glob("/usr/lib/postgresql/*/bin"), reverse=True)), None)
    if not pg and shutil.which("initdb"):
        pg = os.path.dirname(shutil.which("initdb") or "")
    rest = os.environ.get("POSTGREST_BIN") or shutil.which("postgrest")
    if pg and rest and os.path.exists(os.path.join(pg, "initdb")) and os.path.exists(rest):
        return pg, rest
    return None


def _port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@contextmanager
def stack(schema_statements: list[str]):
    """Yields {"rest": url, "service_key": jwt, "psql": callable(sql) -> str}. Everything is removed afterwards."""
    found = binaries()
    if not found:
        raise RuntimeError("Postgres or PostgREST binaries not found")
    pg_bin, rest_bin = found
    root = tempfile.mkdtemp(prefix="walkthru-pg-")
    as_postgres = ["runuser", "-u", "postgres", "--"] if os.geteuid() == 0 else []  # initdb refuses to run as root
    if as_postgres:
        shutil.chown(root, "postgres")
    data, port, rest_port = os.path.join(root, "data"), _port(), _port()
    run = lambda *cmd: subprocess.run([*as_postgres, *cmd], check=True, capture_output=True, text=True)
    run(os.path.join(pg_bin, "initdb"), "-D", data, "-U", "postgres", "--auth=trust", "-E", "UTF8")
    run(os.path.join(pg_bin, "pg_ctl"), "-D", data, "-l", os.path.join(root, "log"), "-w", "-o", f"-p {port} -k {root} -c listen_addresses=127.0.0.1", "start")
    rest = None
    try:
        import psycopg

        dsn = f"postgresql://postgres@127.0.0.1:{port}/postgres"
        with psycopg.connect(dsn, autocommit=True) as conn:
            conn.execute(SUPABASE_STUB)
            for stmt in schema_statements:
                conn.execute(stmt)
        conf = os.path.join(root, "postgrest.conf")
        with open(conf, "w") as f:
            f.write(f'db-uri = "postgresql://authenticator@127.0.0.1:{port}/postgres"\n'
                    f'db-schemas = "public"\ndb-anon-role = "anon"\njwt-secret = "{SECRET}"\n'
                    f'server-host = "127.0.0.1"\nserver-port = {rest_port}\n')
        rest = subprocess.Popen([rest_bin, conf], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        url = f"http://127.0.0.1:{rest_port}"
        for _ in range(100):
            try:
                if httpx.get(url, timeout=1).status_code < 500:
                    break
            except httpx.HTTPError:
                time.sleep(0.1)

        def psql(sql: str, params: tuple | None = None, *, user: str | None = None) -> list[tuple]:
            """Run SQL as the owner, or with `user` as that signed-in browser user would (role authenticated, RLS on)."""
            with psycopg.connect(dsn, autocommit=True) as conn, conn.transaction():
                if user:
                    conn.execute("set local role authenticated")
                    conn.execute("select set_config('request.jwt.claims', %s, true)", (json.dumps({"sub": user, "role": "authenticated"}),))
                cur = conn.execute(sql, params)
                return cur.fetchall() if cur.description else []

        yield {"rest": url, "service_key": jwt({"role": "service_role"}), "psql": psql}
    finally:
        if rest:
            rest.terminate()
            rest.wait(10)
        subprocess.run([*as_postgres, os.path.join(pg_bin, "pg_ctl"), "-D", data, "-m", "immediate", "stop"], capture_output=True, check=False)
        shutil.rmtree(root, ignore_errors=True)


class RestTransport(httpx.HTTPTransport):
    """Lets app.db talk to bare PostgREST: Supabase serves it under /rest/v1."""

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        request.url = request.url.copy_with(path=request.url.path.removeprefix("/rest/v1"))
        return super().handle_request(request)
