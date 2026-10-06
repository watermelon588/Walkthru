"""R-S9 proposed migration 0006 on disposable PostgreSQL, never the configured database: every operation reserves in
the one ledger, with its own allowance per owner and window, and all operations share the funded platform budget."""

import uuid
from datetime import UTC, datetime, timedelta

import psycopg
import pytest

from app import migrate
from tests import test_migrate
from tests.test_run_reservations_sql import END, PRICE, RELEASED, SETTLED, START, dispatch, finish, fund, liability, parallel, reserve

cluster = test_migrate.cluster
conn = test_migrate.conn

DAY = datetime(2026, 10, 6, tzinfo=UTC)
NEXT = DAY + timedelta(days=1)
PUBLIC = "00000000-0000-0000-0000-000000000000"


def work(c, owner, operation, key, allowed=3, units=1, cost=0):
    return c.execute("select public.reserve_work(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                     (owner, operation, key, DAY, NEXT, allowed, units, cost, PRICE)).fetchone()[0]


def test_concurrent_anonymous_scans_cannot_pass_the_daily_public_capacity(conn):
    migrate.up(conn)
    fund(conn)
    out = parallel(conn.info.dsn, [lambda c, i=i: work(c, PUBLIC, "public_scan", f"scan-{i}", allowed=4) for i in range(16)])
    assert sorted(o["status"] for o in out) == ["no_credits"] * 12 + ["reserved"] * 4


def test_units_count_toward_the_allowance_atomically(conn):
    migrate.up(conn)
    fund(conn)
    owner = str(uuid.uuid4())
    # Four comparisons of 3 sites each against a 10-scan day: only 3 fit (9 units); a single scan still fits after.
    out = parallel(conn.info.dsn, [lambda c, i=i: work(c, owner, "scan", f"compare-{i}", allowed=10, units=3) for i in range(4)])
    assert sorted(o["status"] for o in out) == ["no_credits", "reserved", "reserved", "reserved"]
    assert work(conn, owner, "scan", "one-more", allowed=10)["status"] == "reserved"
    assert work(conn, owner, "scan", "too-many", allowed=10)["status"] == "no_credits"


def test_each_operation_has_its_own_allowance_but_one_funded_budget(conn):
    migrate.up(conn)
    fund(conn, daily=1_000)
    owner = str(uuid.uuid4())
    assert work(conn, owner, "scan", "s", allowed=1, cost=400)["status"] == "reserved"
    assert work(conn, owner, "scan", "s2", allowed=1)["status"] == "no_credits"
    assert work(conn, owner, "watch", "w", allowed=1, cost=400)["status"] == "reserved"  # a different allowance
    assert work(conn, owner, "citations", "c", allowed=50, units=10, cost=400)["status"] == "budget"  # the shared budget
    assert reserve(conn, owner, "journey", cost=400)["status"] == "budget"  # journey runs draw on the same budget
    assert liability(conn) == 800


def test_journey_runs_ignore_other_operations_when_counting_credits(conn):
    migrate.up(conn)
    fund(conn)
    owner = str(uuid.uuid4())
    # A scan reservation in exactly the journey run's counting window must not use the run credit.
    same = conn.execute("select public.reserve_work(%s,'scan','same-window',%s,%s,5,1,0,%s)", (owner, START, END, PRICE)).fetchone()[0]
    assert same["status"] == "reserved"
    assert reserve(conn, owner, "run-1", allowed=1)["status"] == "reserved"
    assert conn.execute("select operation from run_reservations where operation_key='run-1'").fetchone()[0] == "run"


def test_released_keys_are_readmitted_but_settled_work_is_never_executed_twice(conn):
    migrate.up(conn)
    fund(conn)
    owner = str(uuid.uuid4())
    first = work(conn, owner, "watch", "watch:site:2026-10-06", allowed=1)
    assert finish(conn, first["id"], RELEASED)  # the site did not answer; nothing was dispatched
    again = work(conn, owner, "watch", "watch:site:2026-10-06", allowed=1)
    assert again == {"status": "reserved", "id": first["id"], "used": 1}  # the job retry is admitted again
    assert dispatch(conn, again["id"]) and finish(conn, again["id"], SETTLED)
    replay = work(conn, owner, "watch", "watch:site:2026-10-06", allowed=1)
    assert replay["status"] == "replayed" and replay["state"] == "settled"  # the caller skips: already done
    assert work(conn, owner, "scan", "watch:site:2026-10-06", allowed=1)["status"] == "conflict"  # different operation


def test_released_journey_run_replays_keep_the_r_s8_answer(conn):
    migrate.up(conn)
    fund(conn)
    owner = str(uuid.uuid4())
    rid = reserve(conn, owner, "run-replayed", allowed=1)["id"]
    assert finish(conn, rid, RELEASED)
    assert reserve(conn, owner, "run-replayed", allowed=1) == {"status": "replayed", "id": rid, "state": "released"}
    assert dispatch(conn, rid) is False  # so the replayed request starts nothing


def test_invalid_work_requests_are_refused(conn):
    migrate.up(conn)
    fund(conn)
    for operation, units in (("teleport", 1), ("run", 2), ("scan", 0), ("scan", 1001)):
        with pytest.raises(psycopg.Error):
            work(conn, str(uuid.uuid4()), operation, "k", units=units)


@pytest.mark.parametrize("role", ["anon", "authenticated"])
def test_customers_and_the_public_cannot_reserve_work(conn, role):
    migrate.up(conn)
    fund(conn)
    conn.execute(f"set role {role}")
    try:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            work(conn, str(uuid.uuid4()), "scan", "mine")
    finally:
        conn.execute("reset role")
    conn.execute("set role service_role")
    try:
        assert work(conn, str(uuid.uuid4()), "scan", "service")["status"] == "reserved"
    finally:
        conn.execute("reset role")


def test_rollback_restores_r_s8_and_reapplies(conn):
    migrate.up(conn)
    fund(conn)
    owner = str(uuid.uuid4())
    assert work(conn, owner, "scan", "gone", units=2)["status"] == "reserved"
    assert reserve(conn, owner, "kept")["status"] == "reserved"
    assert migrate.down(conn) == "0006"
    assert [r[0] for r in conn.execute("select operation_key from run_reservations").fetchall()] == ["kept"]
    assert reserve(conn, owner, "after-rollback")["status"] == "reserved"  # the R-S8 function works again
    with pytest.raises(psycopg.Error):
        work(conn, owner, "scan", "no-function")
    assert migrate.up(conn) == ["0006"]
    assert work(conn, owner, "scan", "back")["status"] == "reserved"
