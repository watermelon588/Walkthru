"""Versioned migrations (app/migrate.py, SD-5.1) against a throwaway local Postgres with Supabase's roles and auth stubs.
Skips when the Postgres server binaries (initdb, pg_ctl) are missing."""

import json
import shutil
import socket
import subprocess
import uuid
from pathlib import Path

import pytest

from app import db, migrate
from tests.live_stack import SUPABASE_STUB
from tests.test_jobs_sql import _bin


@pytest.fixture(scope="module")
def cluster(tmp_path_factory):
    psycopg = pytest.importorskip("psycopg")
    initdb, pg_ctl = _bin("initdb"), _bin("pg_ctl")
    if not initdb or not pg_ctl:
        pytest.skip("Postgres server binaries required")
    data = tmp_path_factory.mktemp("migrate-postgres") / "data"
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    quiet = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}  # pg_ctl's server keeps pipes open on Windows
    subprocess.run([initdb, "-D", str(data), "-A", "trust", "-U", "postgres", "-E", "UTF8"], check=True, **quiet)
    subprocess.run([pg_ctl, "-D", str(data), "-l", str(data.parent / "log"), "-o", f"-h 127.0.0.1 -p {port}", "-w", "start"], check=True, **quiet)
    base = f"host=127.0.0.1 port={port} user=postgres dbname="
    try:
        with psycopg.connect(base + "postgres", autocommit=True) as conn:
            conn.execute("create database supabase_template")
        with psycopg.connect(base + "supabase_template", autocommit=True) as conn:
            conn.execute(SUPABASE_STUB)  # roles are cluster-wide; the rest is copied into each test's database
        yield base
    finally:
        subprocess.run([pg_ctl, "-D", str(data), "-m", "immediate", "stop"], check=False, **quiet)


@pytest.fixture
def conn(cluster):
    """A fresh database that looks like a new Supabase project."""
    import psycopg

    name = "t" + uuid.uuid4().hex[:12]
    with psycopg.connect(cluster + "postgres", autocommit=True) as admin:
        admin.execute(f"create database {name} template supabase_template")
    with migrate.connect(cluster + name) as c:
        yield c


@pytest.fixture
def folder(tmp_path) -> Path:
    """A migrations folder holding the real 0001, for tests that add their own later migrations."""
    shutil.copy(migrate.DIRECTORY / "0001_initial.sql", tmp_path)
    return tmp_path


def tables(conn) -> set[str]:
    return {r[0] for r in conn.execute("select table_name from information_schema.tables where table_schema = 'public'").fetchall()}


def test_a_new_database_gets_every_migration_once(conn):
    assert migrate.up(conn) == [v for v, _ in migrate.files()]
    assert {"runs", "jobs", "rate_limits", "team_messages", "schema_migrations"} <= tables(conn)
    assert migrate.up(conn) == []  # nothing twice
    assert conn.execute("select version, checksum from public.schema_migrations where version = '0001'").fetchone()[1] == migrate.checksum(migrate.DIRECTORY / "0001_initial.sql")


def test_report_and_evidence_rls_follow_membership_removal_without_postgrest(conn):
    """Real policies; no remote accounts, credentials or workspace access grants. Since 0008/0009 a shared report opens
    by id (read_run) but nobody can list other people's shared reports."""
    import psycopg

    migrate.up(conn)
    owner, viewer, team, group = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    conn.execute("insert into auth.users(id) values (%s), (%s)", (owner, viewer))
    for run, public in (("private", False), ("shared", False), ("public", True)):
        conn.execute("insert into runs(id,user_id,site,goal,persona,public,group_id) values (%s,%s,'https://fixture.test','Read','first_timer',%s,%s)",
                     (run, owner, public, group))
        conn.execute("insert into storage.objects(bucket_id,name) values ('run-evidence',%s)", (run + '/step-01.jpg',))
    conn.execute("insert into teams(id,name,owner_id) values (%s,'Local QA',%s)", (team, owner))
    conn.execute("insert into team_members(team_id,user_id,role) values (%s,%s,'viewer')", (team, viewer))
    conn.execute("insert into team_runs(team_id,run_id,shared_by) values (%s,'shared',%s)", (team, owner))

    def act_as(role, user=None):
        # Values are local constants. Claims mimic the auth.uid() input used by PostgREST.
        conn.execute("reset role")
        conn.execute("select set_config('request.jwt.claims', %s, false)", (json.dumps({'sub': str(user)} if user else {}),))
        conn.execute(f"set role {role}")

    def visible(role, user=None):
        act_as(role, user)
        reports = {run for run in ("private", "shared", "public") if conn.execute("select public.read_run(%s)", (run,)).fetchone()[0]}
        evidence = {row[0].split('/')[0] for row in conn.execute("select name from storage.objects")}
        group_runs = {row[0]["id"] for row in conn.execute("select public.read_group_runs(%s)", (group,))}
        assert reports == evidence == group_runs
        return reports

    assert visible('anon') == {'public'}
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("select id from runs")  # the public key cannot list shared reports
    act_as('anon')
    assert "user_id" not in conn.execute("select public.read_run('public')").fetchone()[0]
    assert visible('authenticated', owner) == {'private', 'shared', 'public'}
    assert visible('authenticated', viewer) == {'shared', 'public'}
    assert {row[0] for row in conn.execute("select id from runs")} == {'shared'}  # listing: team shares, not public runs
    assert conn.execute("select count(*) from teams").fetchone()[0] == 1
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("update team_members set role='owner' where user_id=%s", (viewer,))
    conn.execute("reset role")
    conn.execute("delete from team_members where team_id=%s and user_id=%s", (team, viewer))
    assert visible('authenticated', viewer) == {'public'}
    assert conn.execute("select count(*) from teams").fetchone()[0] == 0
    conn.execute("reset role")


def test_a_database_set_up_by_hand_takes_0001_as_its_baseline(conn):
    for statement in db.statements(Path(db.SCHEMA).read_text(encoding="utf-8")):  # how production got its schema so far
        conn.execute(statement)
    assert "0001" in migrate.up(conn)  # re-applying the idempotent baseline succeeds and is recorded
    assert migrate.status(conn)[0] == "applied  0001_initial.sql"


def test_a_failing_migration_leaves_no_trace(conn, folder):
    (folder / "0002_half_done.sql").write_text("create table public.half_done (id int);\nselect no_such_function();\n")
    with pytest.raises(Exception, match="no_such_function"):
        migrate.up(conn, folder)
    assert "half_done" not in tables(conn)  # the first statement was rolled back with the second
    assert [r[0] for r in conn.execute("select version from public.schema_migrations").fetchall()] == ["0001"]


def test_an_edited_migration_is_refused(conn, folder):
    (folder / "0002_flag.sql").write_text("alter table public.runs add column flag boolean;\n")
    migrate.up(conn, folder)
    (folder / "0002_flag.sql").write_text("alter table public.runs add column flag text;\n")
    with pytest.raises(SystemExit, match="0002_flag.sql"):
        migrate.up(conn, folder)
    assert migrate.status(conn, folder)[-1].endswith("(edited since applied)")


def test_down_undoes_only_the_latest_and_only_with_a_down_file(conn, folder):
    (folder / "0002_flag.sql").write_text("alter table public.runs add column flag boolean;\n")
    (folder / "0002_flag.down.sql").write_text("alter table public.runs drop column flag;\n")
    migrate.up(conn, folder)
    column = "select count(*) from information_schema.columns where table_name = 'runs' and column_name = 'flag'"
    assert conn.execute(column).fetchone()[0] == 1
    assert migrate.down(conn, folder) == "0002"
    assert conn.execute(column).fetchone()[0] == 0 and migrate.status(conn, folder)[-1] == "pending  0002_flag.sql"
    with pytest.raises(SystemExit, match="cannot be undone"):
        migrate.down(conn, folder)  # 0001 has no down file


def test_line_endings_do_not_change_a_checksum_and_numbers_must_be_unique(tmp_path):
    (tmp_path / "0001_a.sql").write_bytes(b"select 1;\r\nselect 2;\r\n")
    (tmp_path / "0002_b.sql").write_bytes(b"select 1;\nselect 2;\n")
    assert migrate.checksum(tmp_path / "0001_a.sql") == migrate.checksum(tmp_path / "0002_b.sql")
    (tmp_path / "0002_c.sql").write_text("select 3;")
    with pytest.raises(SystemExit, match="share a number"):
        migrate.files(tmp_path)


def test_link_only_reads_roll_back_cleanly(conn):
    """0009 then 0008 down: anonymous listing returns, then the functions are gone and evidence still follows runs."""
    migrate.up(conn)
    owner = uuid.uuid4()
    conn.execute("insert into auth.users(id) values (%s)", (owner,))
    conn.execute("insert into runs(id,user_id,site,goal,persona,public) values ('pub',%s,'https://fixture.test','Read','first_timer',true)", (owner,))
    conn.execute("insert into storage.objects(bucket_id,name) values ('run-evidence','pub/step-01.jpg')")
    assert migrate.down(conn) == "0009"
    assert migrate.down(conn) == "0008"
    conn.execute("select set_config('request.jwt.claims', '{}', false)")
    conn.execute("set role anon")
    assert [r[0] for r in conn.execute("select id from runs")] == ["pub"]
    assert [r[0] for r in conn.execute("select name from storage.objects")] == ["pub/step-01.jpg"]
    conn.execute("reset role")
    assert conn.execute("select to_regprocedure('public.read_run(text)')").fetchone()[0] is None
