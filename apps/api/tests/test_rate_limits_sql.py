"""The shared rate limit counter (migrations/0001_initial.sql `hit_rate_limit`, SD-2.1) in a throwaway local Postgres."""

from concurrent.futures import ThreadPoolExecutor

import pytest

from tests.test_jobs_sql import sql  # noqa: F401 - the Postgres fixture; its schema block includes the rate limits


@pytest.fixture
def q(sql):  # noqa: F811 - the imported fixture
    sql("truncate public.rate_limits")
    return sql


def hit(q, key="user:a", limit=20, seconds=60) -> int:
    return q("select public.hit_rate_limit(%s, %s, %s)", (key, limit, seconds))[0][0]


def test_racing_requests_get_exactly_the_limit(q):
    # Atomic counting is tested in one window; the next test covers rollover. A 60-second
    # UTC bucket can end during the burst and legitimately admit a second batch. Choose
    # the first fixed bucket ending one hour after setup, using the database's own clock.
    seconds = int(q("select extract(epoch from clock_timestamp())")[0][0]) + 3600
    with ThreadPoolExecutor(10) as pool:
        waits = list(pool.map(lambda _: hit(q, seconds=seconds), range(50)))
    assert waits.count(0) == 20  # never 21 through, however the requests interleave
    assert all(0 < w <= 3600 for w in waits if w)  # the rest are told when the window ends
    assert q("select hits from public.rate_limits") == [(50,)]


def test_keys_are_separate_and_a_new_window_starts_over(q):
    waits = [hit(q, limit=2) for _ in range(3)]
    assert waits[:2] == [0, 0] and 0 < waits[2] <= 60
    assert hit(q, key="user:b", limit=2) == 0  # another user is not affected
    q("update public.rate_limits set window_start = window_start - interval '1 hour' where key = 'user:a'")  # time passed
    assert hit(q, limit=2) == 0 and q("select hits from public.rate_limits where key = 'user:a'") == [(1,)]


def test_browsers_cannot_touch_the_counters(q):
    assert q("select has_table_privilege('anon', 'public.rate_limits', 'select'), has_table_privilege('authenticated', 'public.rate_limits', 'update')") == [(False, False)]
    assert q("select has_function_privilege('anon', 'public.hit_rate_limit(text, integer, integer)', 'execute')") == [(False,)]
