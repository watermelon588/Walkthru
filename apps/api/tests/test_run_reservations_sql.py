"""R-S8 proposed migration on disposable PostgreSQL, never the configured database: atomic admission under real
concurrency, funded-budget limits, replay, crash after dispatch, out-of-order settlement, refunds and permissions."""

import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import psycopg
import pytest
from psycopg.types.json import Jsonb

from app import migrate
from tests import test_migrate

cluster = test_migrate.cluster
conn = test_migrate.conn

START = datetime(2026, 10, 1, tzinfo=UTC)
END = START + timedelta(days=30)
PRICE = "run-caps-2026-10-06"
SETTLED = {"state": "settled", "actual_cost_microusd": None, "reason": "completed", "credit": 1}
RELEASED = {"state": "released", "actual_cost_microusd": 0, "reason": "not_dispatched", "credit": 0}


def fund(c, daily=10**9, monthly=10**10):
    c.execute("insert into spend_budgets(key, limit_microusd) values ('platform_daily', %s), ('platform_monthly', %s) "
              "on conflict (key) do update set limit_microusd = excluded.limit_microusd", (daily, monthly))


def reserve(c, user, key, allowed=3, cost=100):
    return c.execute("select public.reserve_run(%s,%s,%s,%s,%s,%s,%s)", (user, key, START, END, allowed, cost, PRICE)).fetchone()[0]


def dispatch(c, rid):
    return c.execute("select public.mark_reservation_dispatched(%s)", (rid,)).fetchone()[0]


def finish(c, rid, outcome):
    return c.execute("select public.finish_reservation(%s,%s)", (rid, Jsonb(outcome))).fetchone()[0]


def liability(c):
    return c.execute("select public.reservation_liability(%s)", (START - timedelta(days=400),)).fetchone()[0]


def parallel(dsn, calls):
    def one(call):
        with psycopg.connect(dsn, autocommit=True) as c:
            return call(c)
    with ThreadPoolExecutor(max_workers=len(calls)) as executor:
        return list(executor.map(one, calls))


def test_concurrent_starts_cannot_exceed_the_users_credits(conn):
    migrate.up(conn)
    fund(conn)
    user = str(uuid.uuid4())
    out = parallel(conn.info.dsn, [lambda c, i=i: reserve(c, user, f"run-{i}") for i in range(20)])
    assert sorted(o["status"] for o in out) == ["no_credits"] * 17 + ["reserved"] * 3
    assert conn.execute("select count(*) from run_reservations").fetchone()[0] == 3


def test_concurrent_users_cannot_exceed_the_funded_platform_budget(conn):
    migrate.up(conn)
    fund(conn, daily=1_000)
    out = parallel(conn.info.dsn, [lambda c: reserve(c, str(uuid.uuid4()), "run", cost=300) for _ in range(10)])
    assert sorted(o["status"] for o in out) == ["budget"] * 7 + ["reserved"] * 3
    assert liability(conn) == 900


def test_unfunded_platform_fails_closed_and_invalid_input_is_refused(conn):
    migrate.up(conn)
    assert reserve(conn, str(uuid.uuid4()), "run")["status"] == "unfunded"
    fund(conn)
    for bad in ({"key": "has space"}, {"allowed": -1}, {"cost": -5}):
        with pytest.raises(psycopg.Error):
            conn.execute("select public.reserve_run(%s,%s,%s,%s,%s,%s,%s)", (str(uuid.uuid4()), bad.get("key", "k"), START, END,
                                                                             bad.get("allowed", 1), bad.get("cost", 1), PRICE))


def test_replays_return_the_same_reservation_and_conflicting_terms_are_refused(conn):
    migrate.up(conn)
    fund(conn)
    user = str(uuid.uuid4())
    out = parallel(conn.info.dsn, [lambda c: reserve(c, user, "same-run") for _ in range(8)])
    ids = {o["id"] for o in out}
    assert len(ids) == 1 and sorted(o["status"] for o in out) == ["replayed"] * 7 + ["reserved"]
    assert reserve(conn, user, "same-run", cost=999)["status"] == "conflict"
    assert conn.execute("select count(*) from run_reservations").fetchone()[0] == 1


def test_release_only_before_dispatch_and_settlement_is_idempotent(conn):
    migrate.up(conn)
    fund(conn)
    user = str(uuid.uuid4())
    early = reserve(conn, user, "early", allowed=1)["id"]
    assert finish(conn, early, RELEASED) and finish(conn, early, RELEASED)  # identical replay
    assert reserve(conn, user, "next", allowed=1)["status"] == "reserved"  # the released credit came back
    late = reserve(conn, user, "late", allowed=2)["id"]
    assert dispatch(conn, late)
    assert finish(conn, late, RELEASED) is False  # dispatched work can never be released
    assert finish(conn, late, SETTLED) and finish(conn, late, SETTLED)
    assert finish(conn, late, SETTLED | {"actual_cost_microusd": 5}) is False  # conflicting terminal payload
    assert finish(conn, uuid.uuid4(), SETTLED) is False
    for bad in (SETTLED | {"reason": "lease_expired"}, SETTLED | {"credit": 2}, RELEASED | {"actual_cost_microusd": 3}, {**SETTLED, "extra": 1}):
        with pytest.raises(psycopg.Error):
            finish(conn, late, bad)


def test_refused_goal_returns_the_credit_but_keeps_the_provider_cost(conn):
    migrate.up(conn)
    fund(conn)
    user = str(uuid.uuid4())
    rid = reserve(conn, user, "refused", allowed=1, cost=250)["id"]
    assert dispatch(conn, rid)
    assert finish(conn, rid, {"state": "settled", "actual_cost_microusd": None, "reason": "refused", "credit": 0})
    assert reserve(conn, user, "after", allowed=1, cost=0)["status"] == "reserved"
    assert liability(conn) == 250  # unknown actual cost stays counted at the reserved maximum


def test_crash_after_provider_response_keeps_the_liability_until_settled(conn):
    migrate.up(conn)
    fund(conn)
    user = str(uuid.uuid4())
    script = """
import sys, psycopg
with psycopg.connect(sys.argv[1], autocommit=True) as c:
    rid = c.execute("select public.reserve_run(%s,'crashed',%s,%s,1,400,'run-caps-2026-10-06')", (sys.argv[2], sys.argv[3], sys.argv[4])).fetchone()[0]['id']
    assert c.execute('select public.mark_reservation_dispatched(%s)', (rid,)).fetchone()[0]
    print(rid)
"""
    rid = subprocess.run([sys.executable, "-c", script, conn.info.dsn, user, START.isoformat(), END.isoformat()],
                         check=True, capture_output=True, text=True).stdout.strip()
    with psycopg.connect(conn.info.dsn, autocommit=True) as restarted:  # the worker died; a new process takes over
        assert restarted.execute("select state, dispatched from run_reservations where id=%s", (rid,)).fetchone() == ("reserved", True)
        assert finish(restarted, rid, RELEASED) is False
        assert reserve(restarted, user, "another", allowed=1)["status"] == "no_credits"
        assert liability(restarted) == 400
        assert finish(restarted, rid, {"state": "settled", "actual_cost_microusd": 120, "reason": "reconciled", "credit": 1})
        assert liability(restarted) == 120


def test_out_of_order_messages_do_not_reopen_or_free_a_reservation(conn):
    migrate.up(conn)
    fund(conn)
    rid = reserve(conn, str(uuid.uuid4()), "late-mark")["id"]
    assert finish(conn, rid, SETTLED)
    assert dispatch(conn, rid)  # a late dispatch mark acknowledges without reopening
    assert conn.execute("select state from run_reservations where id=%s", (rid,)).fetchone()[0] == "settled"
    assert finish(conn, rid, RELEASED) is False
    released = reserve(conn, str(uuid.uuid4()), "freed")["id"]
    assert finish(conn, released, RELEASED)
    assert dispatch(conn, released) is False  # never dispatch on a released reservation


def test_refunds_are_founder_owned_return_the_credit_and_keep_spent_cost(conn):
    migrate.up(conn)
    fund(conn)
    user = str(uuid.uuid4())
    rid = reserve(conn, user, "paid", allowed=1, cost=300)["id"]
    assert dispatch(conn, rid) and finish(conn, rid, SETTLED | {"actual_cost_microusd": 80})
    with pytest.raises(psycopg.Error):
        conn.execute("select public.refund_reservation(%s,'system','auto')", (rid,))
    refund = lambda: conn.execute("select public.refund_reservation(%s,'founder','Customer refund 2026-10-06')", (rid,)).fetchone()[0]
    assert refund() and refund()
    assert conn.execute("select public.refund_reservation(%s,'founder','different reason')", (rid,)).fetchone()[0] is False
    assert reserve(conn, user, "again", allowed=1, cost=0)["status"] == "reserved"
    assert liability(conn) == 80


@pytest.mark.parametrize("role", ["anon", "authenticated"])
def test_customers_and_the_public_can_neither_read_nor_call(conn, role):
    migrate.up(conn)
    fund(conn)
    rid = reserve(conn, str(uuid.uuid4()), "run")["id"]
    conn.execute(f"set role {role}")
    try:
        for statement in ("select * from public.run_reservations", "select * from public.spend_budgets"):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute(statement)
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            reserve(conn, str(uuid.uuid4()), "mine")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            finish(conn, rid, SETTLED)
    finally:
        conn.execute("reset role")


def test_service_role_reserves_and_settles_but_cannot_write_rows_refund_or_fund(conn):
    migrate.up(conn)
    fund(conn)
    conn.execute("set role service_role")
    try:
        rid = reserve(conn, str(uuid.uuid4()), "run")["id"]
        assert dispatch(conn, rid) and finish(conn, rid, SETTLED)
        for statement in ("delete from run_reservations", "update run_reservations set state = 'released'",
                          "update spend_budgets set limit_microusd = 0"):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute(statement)
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("select public.refund_reservation(%s,'founder','x')", (rid,))
    finally:
        conn.execute("reset role")


def test_rollback_and_reapply(conn):
    migrate.up(conn)
    later = [v for v, _ in migrate.files() if v > "0005"]  # newer migrations (0006 work admission) roll back first
    assert [migrate.down(conn) for _ in range(len(later) + 1)] == [*reversed(later), "0005"]
    assert {"run_reservations", "spend_budgets"}.isdisjoint(test_migrate.tables(conn))
    migrate.up(conn)
    fund(conn)
    assert reserve(conn, str(uuid.uuid4()), "run")["status"] == "reserved"
