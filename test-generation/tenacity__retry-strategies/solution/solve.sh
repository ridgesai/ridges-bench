#!/bin/bash
set -euo pipefail
cd /app
mkdir -p regression_tests
cat > regression_tests/test_retry_strategies.py <<'PY'
"""Reference regression suite for tenacity's retry strategies."""
import random
from datetime import timedelta

import pytest

import tenacity
from tenacity import (
    RetryCallState,
    RetryError,
    Retrying,
    TryAgain,
    retry,
    retry_all,
    retry_any,
    retry_if_exception_message,
    retry_if_exception_type,
    retry_if_not_exception_type,
    retry_if_not_result,
    retry_if_result,
    stop_after_attempt,
    stop_after_delay,
    stop_all,
    stop_any,
    stop_before_delay,
    stop_never,
    wait_chain,
    wait_combine,
    wait_exponential,
    wait_fixed,
    wait_incrementing,
    wait_none,
    wait_random,
)


class Sleeps(list):
    def __call__(self, seconds):
        self.append(seconds)


def failing(n, exc=ValueError, result="done"):
    """Callable that raises ``exc`` for its first ``n`` calls."""
    calls = []

    def fn():
        calls.append(len(calls) + 1)
        if len(calls) <= n:
            raise exc("boom %d" % len(calls))
        return result

    fn.calls = calls
    return fn


def returning(*values):
    calls = []

    def fn():
        calls.append(1)
        return values[min(len(calls), len(values)) - 1]

    fn.calls = calls
    return fn


def make_state(attempt=1, seconds=None, upcoming=0.0, result=None, exc=None):
    state = RetryCallState(retry_object=Retrying(), fn=None, args=(), kwargs={})
    state.attempt_number = attempt
    if exc is not None:
        state.set_exception((type(exc), exc, None))
    else:
        state.set_result(result)
    if seconds is not None:
        state.start_time = 100.0
        state.outcome_timestamp = 100.0 + seconds
    state.upcoming_sleep = upcoming
    return state


# ---------------------------------------------------------------- stop


def test_stop_after_attempt_counts_calls():
    sleeps = Sleeps()
    fn = failing(10)
    with pytest.raises(RetryError) as info:
        Retrying(sleep=sleeps, stop=stop_after_attempt(3))(fn)
    assert fn.calls == [1, 2, 3]
    assert info.value.last_attempt.attempt_number == 3
    assert len(sleeps) == 2


def test_stop_after_attempt_direct():
    s = stop_after_attempt(3)
    assert s(make_state(attempt=1)) is False
    assert s(make_state(attempt=2)) is False
    assert s(make_state(attempt=3)) is True
    assert s(make_state(attempt=4)) is True


def test_stop_after_attempt_one_means_no_retry():
    fn = failing(5)
    with pytest.raises(RetryError):
        Retrying(sleep=Sleeps(), stop=stop_after_attempt(1))(fn)
    assert fn.calls == [1]


def test_stop_after_delay_direct():
    s = stop_after_delay(5)
    assert s(make_state(seconds=4.9)) is False
    assert s(make_state(seconds=5.0)) is True
    assert s(make_state(seconds=7.0)) is True
    td = stop_after_delay(timedelta(seconds=2))
    assert td(make_state(seconds=1.5)) is False
    assert td(make_state(seconds=2.0)) is True


def test_stop_after_delay_through_retrying():
    fn = failing(5)
    with pytest.raises(RetryError):
        Retrying(sleep=Sleeps(), stop=stop_after_delay(0))(fn)
    assert fn.calls == [1]
    fn = failing(3)
    assert Retrying(sleep=Sleeps(), stop=stop_after_delay(3600))(fn) == "done"
    assert fn.calls == [1, 2, 3, 4]


def test_stop_before_delay_direct():
    s = stop_before_delay(5)
    assert s(make_state(seconds=3.0, upcoming=1.5)) is False
    assert s(make_state(seconds=3.0, upcoming=2.0)) is True
    assert s(make_state(seconds=3.0, upcoming=3.0)) is True
    assert s(make_state(seconds=0.0, upcoming=0.0)) is False


def test_stop_before_delay_uses_upcoming_wait():
    fn = failing(5)
    with pytest.raises(RetryError):
        Retrying(sleep=Sleeps(), wait=wait_fixed(1000), stop=stop_before_delay(500))(fn)
    assert fn.calls == [1]
    fn = failing(2)
    sleeps = Sleeps()
    Retrying(sleep=sleeps, wait=wait_fixed(1), stop=stop_before_delay(3600))(fn)
    assert sleeps == [1.0, 1.0]


def test_stop_or_combination():
    fn = failing(10)
    with pytest.raises(RetryError):
        Retrying(sleep=Sleeps(), stop=stop_after_attempt(2) | stop_after_attempt(5))(fn)
    assert len(fn.calls) == 2
    assert isinstance(stop_after_attempt(2) | stop_after_attempt(5), stop_any)


def test_stop_and_combination():
    fn = failing(10)
    with pytest.raises(RetryError):
        Retrying(sleep=Sleeps(), stop=stop_after_attempt(2) & stop_after_attempt(5))(fn)
    assert len(fn.calls) == 5
    assert isinstance(stop_after_attempt(2) & stop_after_attempt(5), stop_all)


def test_stop_any_all_direct():
    st = make_state(attempt=3, seconds=1.0)
    assert stop_any(stop_after_attempt(5), stop_after_delay(1))(st) is True
    assert stop_any(stop_after_attempt(5), stop_after_delay(2))(st) is False
    assert stop_all(stop_after_attempt(3), stop_after_delay(1))(st) is True
    assert stop_all(stop_after_attempt(3), stop_after_delay(2))(st) is False
    assert stop_never(st) is False


# ---------------------------------------------------------------- wait


def test_wait_fixed_and_none():
    assert wait_fixed(3)(make_state(attempt=1)) == 3
    assert wait_fixed(3)(make_state(attempt=9)) == 3
    assert wait_fixed(timedelta(milliseconds=1500))(make_state()) == 1.5
    assert wait_none()(make_state(attempt=4)) == 0


def test_wait_fixed_sleeps_through_retrying():
    sleeps = Sleeps()
    fn = failing(3)
    assert Retrying(sleep=sleeps, wait=wait_fixed(2))(fn) == "done"
    assert sleeps == [2, 2, 2]


def test_wait_random_bounds():
    random.seed(1234)
    w = wait_random(min=1, max=3)
    values = [w(make_state(attempt=i % 5 + 1)) for i in range(300)]
    assert all(1 <= v <= 3 for v in values)
    assert min(values) < 1.2
    assert max(values) > 2.8
    random.seed(99)
    d = wait_random()
    defaults = [d(make_state()) for _ in range(300)]
    assert all(0 <= v <= 1 for v in defaults)
    assert max(defaults) > 0.9
    assert min(defaults) < 0.1


def test_wait_incrementing():
    w = wait_incrementing(start=1, increment=2, max=6)
    assert [w(make_state(attempt=n)) for n in range(1, 6)] == [1, 3, 5, 6, 6]
    d = wait_incrementing()
    assert [d(make_state(attempt=n)) for n in (1, 2, 3)] == [0, 100, 200]
    neg = wait_incrementing(start=5, increment=-2)
    assert [neg(make_state(attempt=n)) for n in (1, 2, 3, 4, 5)] == [5, 3, 1, 0, 0]


def test_wait_exponential_defaults():
    w = wait_exponential()
    assert [w(make_state(attempt=n)) for n in range(1, 6)] == [1, 2, 4, 8, 16]


def test_wait_exponential_options():
    w = wait_exponential(multiplier=3, max=20)
    assert [w(make_state(attempt=n)) for n in range(1, 6)] == [3, 6, 12, 20, 20]
    w = wait_exponential(min=5)
    assert [w(make_state(attempt=n)) for n in range(1, 6)] == [5, 5, 5, 8, 16]
    w = wait_exponential(exp_base=3)
    assert [w(make_state(attempt=n)) for n in range(1, 5)] == [1, 3, 9, 27]
    w = wait_exponential(multiplier=0.5, max=timedelta(seconds=3))
    assert [w(make_state(attempt=n)) for n in range(1, 6)] == [0.5, 1, 2, 3, 3]


def test_wait_exponential_degenerate_parameters():
    w = wait_exponential(multiplier=2, exp_base=1)
    assert [w(make_state(attempt=n)) for n in (1, 2, 10)] == [2, 2, 2]
    w = wait_exponential(multiplier=0)
    assert [w(make_state(attempt=n)) for n in (1, 5)] == [0, 0]
    w = wait_exponential(max=0)
    assert [w(make_state(attempt=n)) for n in (1, 5)] == [0, 0]


def test_wait_exponential_large_attempts_capped():
    w = wait_exponential(max=60)
    assert w(make_state(attempt=5000)) == 60
    assert w(make_state(attempt=7)) == 60
    assert w(make_state(attempt=6)) == 32
    w = wait_exponential(multiplier=1, max=64)
    assert w(make_state(attempt=7)) == 64
    assert w(make_state(attempt=8)) == 64


def test_wait_chain():
    w = wait_chain(wait_fixed(1), wait_fixed(2), wait_fixed(3))
    assert [w(make_state(attempt=n)) for n in range(1, 7)] == [1, 2, 3, 3, 3, 3]
    with pytest.raises(Exception):
        wait_chain()


def test_wait_chain_through_retrying():
    sleeps = Sleeps()
    fn = failing(4)
    Retrying(sleep=sleeps, wait=wait_chain(wait_fixed(5), wait_fixed(7)))(fn)
    assert sleeps == [5, 7, 7, 7]


def test_wait_addition():
    w = wait_fixed(1) + wait_fixed(2)
    assert isinstance(w, wait_combine)
    assert w(make_state()) == 3
    w = wait_fixed(1) + wait_incrementing(start=0, increment=10)
    assert [w(make_state(attempt=n)) for n in (1, 2, 3)] == [1, 11, 21]
    total = sum([wait_fixed(1), wait_fixed(2), wait_fixed(4)])
    assert total(make_state()) == 7
    assert wait_combine(wait_fixed(1), wait_fixed(1), wait_fixed(1))(make_state()) == 3


def test_wait_exponential_through_retrying():
    sleeps = Sleeps()
    fn = failing(5)
    Retrying(sleep=sleeps, wait=wait_exponential(multiplier=1, max=10))(fn)
    assert sleeps == [1, 2, 4, 8, 10]


# ---------------------------------------------------------------- retry conditions


def test_default_retries_exceptions_until_success():
    fn = failing(3)
    assert Retrying(sleep=Sleeps())(fn) == "done"
    assert fn.calls == [1, 2, 3, 4]


def test_default_does_not_retry_base_exceptions():
    fn = failing(3, exc=KeyboardInterrupt)
    with pytest.raises(KeyboardInterrupt):
        Retrying(sleep=Sleeps())(fn)
    assert fn.calls == [1]


def test_retry_if_exception_type():
    r = Retrying(sleep=Sleeps(), retry=retry_if_exception_type(IOError))
    fn = failing(2, exc=IOError)
    assert r(fn) == "done"
    assert len(fn.calls) == 3
    fn = failing(2, exc=KeyError)
    with pytest.raises(KeyError):
        r(fn)
    assert len(fn.calls) == 1
    r = Retrying(sleep=Sleeps(), retry=retry_if_exception_type((KeyError, TypeError)))
    fn = failing(2, exc=TypeError)
    assert r(fn) == "done"


def test_retry_if_exception_type_does_not_retry_results():
    fn = returning(None, 1)
    assert Retrying(sleep=Sleeps(), retry=retry_if_exception_type())(fn) is None
    assert len(fn.calls) == 1


def test_retry_if_not_exception_type():
    r = Retrying(sleep=Sleeps(), retry=retry_if_not_exception_type(KeyError))
    fn = failing(2, exc=ValueError)
    assert r(fn) == "done"
    fn = failing(2, exc=KeyError)
    with pytest.raises(KeyError):
        r(fn)
    assert len(fn.calls) == 1


def test_retry_if_result():
    fn = returning(None, None, 5)
    r = Retrying(sleep=Sleeps(), retry=retry_if_result(lambda x: x is None))
    assert r(fn) == 5
    assert len(fn.calls) == 3
    fn = failing(1)
    with pytest.raises(ValueError):
        r(fn)
    assert len(fn.calls) == 1


def test_retry_if_not_result():
    fn = returning(1, 2, 3, 4)
    r = Retrying(sleep=Sleeps(), retry=retry_if_not_result(lambda x: x >= 3))
    assert r(fn) == 3
    assert len(fn.calls) == 3
    fn = failing(1, exc=KeyError)
    with pytest.raises(KeyError):
        r(fn)


def test_retry_if_exception_message_equal():
    def raiser(messages):
        it = iter(messages)

        def fn():
            m = next(it)
            if m is None:
                return "ok"
            raise ValueError(m)

        return fn

    r = Retrying(sleep=Sleeps(), retry=retry_if_exception_message(message="boom"))
    assert r(raiser(["boom", "boom", None])) == "ok"
    with pytest.raises(ValueError):
        r(raiser(["boom", "other", None]))
    with pytest.raises(ValueError):
        r(raiser(["boom!", None]))


def test_retry_if_exception_message_match():
    def raiser(messages):
        it = iter(messages)

        def fn():
            m = next(it)
            if m is None:
                return "ok"
            raise ValueError(m)

        return fn

    r = Retrying(sleep=Sleeps(), retry=retry_if_exception_message(match="bo+m"))
    assert r(raiser(["boom", "booooom tail", None])) == "ok"
    with pytest.raises(ValueError):
        r(raiser(["a boom", None]))


def test_retry_if_exception_message_arguments():
    with pytest.raises(Exception):
        retry_if_exception_message()
    with pytest.raises(Exception):
        retry_if_exception_message(message="a", match="a")


def test_retry_if_exception_message_ignores_results():
    fn = returning("boom", "x")
    r = Retrying(sleep=Sleeps(), retry=retry_if_exception_message(message="boom"))
    assert r(fn) == "boom"


def test_retry_or_combination():
    cond = retry_if_result(lambda x: x is None) | retry_if_exception_type(KeyError)
    assert isinstance(cond, retry_any)
    fn = returning(None, 7)
    assert Retrying(sleep=Sleeps(), retry=cond)(fn) == 7
    fn = failing(2, exc=KeyError, result=8)
    assert Retrying(sleep=Sleeps(), retry=cond)(fn) == 8
    fn = failing(1, exc=ValueError)
    with pytest.raises(ValueError):
        Retrying(sleep=Sleeps(), retry=cond)(fn)


def test_retry_and_combination():
    cond = retry_if_exception_type(ValueError) & retry_if_exception_message(match="retry")
    assert isinstance(cond, retry_all)
    calls = []

    def fn():
        calls.append(1)
        if len(calls) < 3:
            raise ValueError("retry me")
        raise ValueError("final")

    with pytest.raises(ValueError):
        Retrying(sleep=Sleeps(), retry=cond)(fn)
    assert len(calls) == 3


def test_retry_combination_chains_and_callables():
    three = retry_if_result(lambda x: x == 1) | retry_if_result(lambda x: x == 2) | retry_if_result(lambda x: x == 3)
    assert isinstance(three, retry_any)
    assert len(three.retries) == 3
    fn = returning(1, 2, 3, 4)
    assert Retrying(sleep=Sleeps(), retry=three)(fn) == 4
    both = retry_if_result(lambda x: x > 0) & retry_if_result(lambda x: x < 10) & retry_if_result(lambda x: x != 5)
    assert len(both.retries) == 3
    fn = returning(3, 5)
    assert Retrying(sleep=Sleeps(), retry=both)(fn) == 5
    nested = retry_if_result(lambda x: x == 1) | (retry_if_result(lambda x: x == 2) | retry_if_result(lambda x: x == 3))
    assert Retrying(sleep=Sleeps(), retry=nested)(returning(1, 2, 3, 4)) == 4
    nested_all = retry_if_result(lambda x: x > 0) & (retry_if_result(lambda x: x < 10) & retry_if_result(lambda x: x != 5))
    assert Retrying(sleep=Sleeps(), retry=nested_all)(returning(3, 5)) == 5
    st = make_state(result=3)
    assert retry_any(lambda s: False, lambda s: True)(st) is True
    assert retry_any(lambda s: False, lambda s: False)(st) is False
    assert retry_all(lambda s: True, lambda s: False)(st) is False
    assert retry_all(lambda s: True, lambda s: True)(st) is True


def test_try_again_forces_retry():
    calls = []

    def fn():
        calls.append(1)
        if len(calls) < 3:
            raise TryAgain
        return "ok"

    r = Retrying(sleep=Sleeps(), retry=retry_if_result(lambda x: False))
    assert r(fn) == "ok"
    assert len(calls) == 3


# ---------------------------------------------------------------- errors, reraise, callbacks


def test_retry_error_wraps_last_attempt():
    fn = failing(10)
    with pytest.raises(RetryError) as info:
        Retrying(sleep=Sleeps(), stop=stop_after_attempt(2))(fn)
    err = info.value
    assert err.last_attempt.failed
    assert str(err.last_attempt.exception()) == "boom 2"
    assert isinstance(err.__cause__, ValueError)


def test_retry_error_on_result_condition():
    fn = returning(None)
    with pytest.raises(RetryError) as info:
        Retrying(sleep=Sleeps(), stop=stop_after_attempt(3), retry=retry_if_result(lambda x: x is None))(fn)
    assert info.value.last_attempt.failed is False
    assert info.value.last_attempt.result() is None
    assert info.value.last_attempt.attempt_number == 3


def test_reraise_raises_original_exception():
    fn = failing(10, exc=KeyError)
    with pytest.raises(KeyError) as info:
        Retrying(sleep=Sleeps(), stop=stop_after_attempt(3), reraise=True)(fn)
    assert info.value.args == ("boom 3",)
    assert len(fn.calls) == 3


def test_reraise_with_result_condition_raises_retry_error():
    fn = returning(0)
    with pytest.raises(RetryError):
        Retrying(sleep=Sleeps(), stop=stop_after_attempt(2), reraise=True, retry=retry_if_result(lambda x: x == 0))(fn)


def test_retry_error_callback_supplies_result():
    seen = []

    def callback(state):
        seen.append((state.attempt_number, state.outcome.failed))
        return "fallback"

    fn = failing(10)
    r = Retrying(sleep=Sleeps(), stop=stop_after_attempt(4), retry_error_callback=callback)
    assert r(fn) == "fallback"
    assert seen == [(4, True)]
    assert len(fn.calls) == 4


def test_retry_error_callback_not_used_on_success():
    called = []
    fn = failing(1)
    r = Retrying(sleep=Sleeps(), stop=stop_after_attempt(4), retry_error_callback=called.append)
    assert r(fn) == "done"
    assert called == []


def test_custom_retry_error_cls():
    class MyError(RetryError):
        pass

    with pytest.raises(MyError):
        Retrying(sleep=Sleeps(), stop=stop_after_attempt(2), retry_error_cls=MyError)(failing(5))


# ---------------------------------------------------------------- hooks


def test_before_and_after_hooks():
    events = []

    def before(state):
        assert state.next_action is None
        assert state.outcome is None
        events.append(("before", state.attempt_number))

    def after(state):
        events.append(("after", state.attempt_number, state.outcome.failed))

    fn = failing(2)
    assert Retrying(sleep=Sleeps(), before=before, after=after)(fn) == "done"
    assert events == [
        ("before", 1),
        ("after", 1, True),
        ("before", 2),
        ("after", 2, True),
        ("before", 3),
    ]


def test_hooks_when_giving_up():
    events = []
    fn = failing(10)
    with pytest.raises(RetryError):
        Retrying(
            sleep=Sleeps(),
            stop=stop_after_attempt(2),
            before=lambda s: events.append(("before", s.attempt_number)),
            after=lambda s: events.append(("after", s.attempt_number)),
            before_sleep=lambda s: events.append(("before_sleep", s.attempt_number, s.next_action.sleep)),
        )(fn)
    assert events == [("before", 1), ("after", 1), ("before_sleep", 1, 0.0), ("before", 2), ("after", 2)]


def test_before_sleep_sees_upcoming_wait_and_idle_time():
    seen = []

    def before_sleep(state):
        seen.append((state.attempt_number, state.upcoming_sleep, state.idle_for))

    sleeps = Sleeps()
    Retrying(sleep=sleeps, wait=wait_incrementing(start=1, increment=1), before_sleep=before_sleep)(failing(3))
    assert seen == [(1, 1, 1), (2, 2, 3), (3, 3, 6)]
    assert sleeps == [1, 2, 3]


# ---------------------------------------------------------------- statistics


def test_statistics_on_decorated_function():
    sleeps = Sleeps()
    calls = []

    @retry(sleep=sleeps, wait=wait_fixed(2), stop=stop_after_attempt(5))
    def fn():
        calls.append(1)
        if len(calls) < 3:
            raise ValueError
        return "ok"

    assert fn() == "ok"
    stats = fn.statistics
    assert stats["attempt_number"] == 3
    assert stats["idle_for"] == 4
    assert "start_time" in stats
    assert stats["delay_since_first_attempt"] >= 0


def test_statistics_on_retrying_object():
    r = Retrying(sleep=Sleeps(), wait=wait_fixed(1.5), stop=stop_after_attempt(4))
    with pytest.raises(RetryError):
        r(failing(10))
    assert r.statistics["attempt_number"] == 4
    assert r.statistics["idle_for"] == 4.5
    r(failing(0))
    assert r.statistics["attempt_number"] == 1
    assert r.statistics["idle_for"] == 0


# ---------------------------------------------------------------- decorator and Retrying API


def test_decorator_without_arguments():
    calls = []

    @retry
    def fn(x, y=2):
        """doc"""
        calls.append(1)
        if len(calls) < 3:
            raise ValueError
        return x + y

    assert fn(1, y=5) == 6
    assert len(calls) == 3
    assert fn.__name__ == "fn"
    assert fn.__doc__ == "doc"


def test_decorator_passes_arguments_and_retry_with():
    seen = []

    @retry(stop=stop_after_attempt(2), sleep=Sleeps())
    def fn(a, b):
        seen.append((a, b))
        raise ValueError

    with pytest.raises(RetryError):
        fn(1, b=2)
    assert seen == [(1, 2), (1, 2)]
    seen.clear()
    with pytest.raises(RetryError):
        fn.retry_with(stop=stop_after_attempt(4))(3, 4)
    assert seen == [(3, 4)] * 4
    assert isinstance(fn.retry, Retrying)


def test_retrying_iteration_protocol():
    attempts = []
    for attempt in Retrying(sleep=Sleeps(), stop=stop_after_attempt(5)):
        with attempt:
            attempts.append(attempt.retry_state.attempt_number)
            if len(attempts) < 3:
                raise ValueError
    assert attempts == [1, 2, 3]


def test_retrying_iteration_sleeps_between_attempts():
    sleeps = Sleeps()
    count = 0
    for attempt in Retrying(sleep=sleeps, wait=wait_incrementing(start=2, increment=3)):
        with attempt:
            count += 1
            if count < 4:
                raise ValueError
    assert sleeps == [2, 5, 8]


def test_retrying_iteration_gives_up():
    attempts = []
    with pytest.raises(RetryError):
        for attempt in Retrying(sleep=Sleeps(), stop=stop_after_attempt(2)):
            with attempt:
                attempts.append(1)
                raise ValueError
    assert len(attempts) == 2


def test_retrying_iteration_reraise():
    with pytest.raises(KeyError):
        for attempt in Retrying(sleep=Sleeps(), stop=stop_after_attempt(2), reraise=True):
            with attempt:
                raise KeyError("x")


def test_disabled_retrying_calls_once():
    fn = failing(1)
    with pytest.raises(ValueError):
        retry(enabled=False, sleep=Sleeps())(fn)()
    assert fn.calls == [1]

    @retry(enabled=False)
    def add(a, b=1, *, c=0):
        return (a, b, c)

    assert add(1, b=2, c=3) == (1, 2, 3)
    assert add(5) == (5, 1, 0)


def test_retrying_passes_arguments():
    seen = []

    def fn(*args, **kwargs):
        seen.append((args, kwargs))
        return len(seen)

    assert Retrying(sleep=Sleeps())(fn, 1, 2, k=3) == 1
    assert seen == [((1, 2), {"k": 3})]


def test_retry_state_attributes_in_callback():
    captured = {}

    def callback(state):
        captured["fn"] = state.fn
        captured["args"] = state.args
        captured["kwargs"] = state.kwargs
        captured["idle_for"] = state.idle_for
        return None

    def fn(a, b=None):
        raise ValueError

    Retrying(sleep=Sleeps(), wait=wait_fixed(0.5), stop=stop_after_attempt(3), retry_error_callback=callback)(fn, 1, b=2)
    assert captured == {"fn": fn, "args": (1,), "kwargs": {"b": 2}, "idle_for": 1.0}


def test_copy_keeps_and_overrides_settings():
    base = Retrying(sleep=Sleeps(), stop=stop_after_attempt(2), reraise=True)
    clone = base.copy(stop=stop_after_attempt(4))
    fn = failing(10, exc=KeyError)
    with pytest.raises(KeyError):
        clone(fn)
    assert len(fn.calls) == 4
    fn = failing(10, exc=KeyError)
    with pytest.raises(KeyError):
        base.copy()(fn)
    assert len(fn.calls) == 2


def test_module_exports():
    assert tenacity.retry is retry
    assert tenacity.Retrying is Retrying
PY
# Stage the new files so the oracle control sees them in `git diff HEAD` (runs inside the task container).
git add -A regression_tests
