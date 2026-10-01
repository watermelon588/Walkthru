"""Process-local provider health; shared across model/schema instances."""

from contextlib import contextmanager
from dataclasses import dataclass
from threading import Lock
from time import monotonic

FAILURES = 3
COOLDOWN = 60


@dataclass
class _State:
    failures: int = 0
    until: float = 0
    probing: bool = False
    generation: int = 0


_states: dict[str, _State] = {}
_lock = Lock()


class CircuitOpen(RuntimeError):
    """Skip this provider without sleeping or issuing another request."""


def available(provider: str) -> bool:
    """Advisory precheck for queues; guard still admits at most one recovery probe."""
    with _lock:
        state = _states.get(provider)
        return state is None or (not state.probing and state.until <= monotonic())


@contextmanager
def guard(provider: str):
    """Wrap provider work only, never database writes or browser/graph mutations.

    Count consecutive failed calls in completion order. Old in-flight results cannot close a newer circuit.
    Locks protect admission/state only, never network work. ContextDecorator also supports regular functions.
    """
    with _lock:
        state = _states.setdefault(provider, _State())
        if state.probing or state.until > monotonic():
            raise CircuitOpen(f"{provider} is temporarily unavailable; try another provider")
        if state.until:
            state.probing = True
        generation = state.generation
    failed = False
    try:
        yield
    except BaseException:
        failed = True
        raise
    finally:
        with _lock:
            if state.generation == generation:
                if failed:
                    state.failures += 1
                    if state.probing or state.failures >= FAILURES:
                        state.until = monotonic() + COOLDOWN
                        state.probing = False
                        state.generation += 1
                else:
                    if state.probing:
                        state.generation += 1
                    state.failures = 0
                    state.until = 0
                    state.probing = False
