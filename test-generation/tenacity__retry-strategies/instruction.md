# Build a regression test suite for tenacity's retry controller and strategies

The repository at `/app` is **tenacity 9.2.0** (commit `a2af454`), a library that retries a function call until
it succeeds or a stop condition is met. The maintainers are about to refactor `tenacity/__init__.py`,
`tenacity/stop.py`, `tenacity/wait.py` and `tenacity/retry.py` and need a behavioral safety net for its documented
public API first: the retry controller, its stop, wait and retry strategies, its hooks and its statistics. Your job
is to write that suite.

## What the suite must do

- Catch any behavioral regression in this API, however small, including
  subtle edge and boundary cases.
- Keep passing on any behavior-preserving rewrite of it: the package is about
  to be restructured, so test through the public API and its documented
  contract, never through internals.

Cover normal behavior, edge and boundary cases, invalid or unusual inputs,
interactions between related features, state and sequencing, and places where
a small implementation change could alter results.

## Scope

The documented observable behavior of the following, as described in the documentation under `doc/source/`, the
README and the docstrings:

- The controller: the `retry` decorator (bare and with arguments, `retry_with`, `statistics`) and `Retrying`
  (called with a function and its arguments, iterated with `for attempt in Retrying(...)` and `with attempt:`, and
  `copy`), with all of their options: `sleep`, `stop`, `wait`, `retry`, `before`, `after`, `before_sleep`,
  `reraise`, `retry_error_cls`, `retry_error_callback` and `enabled`;
- stop strategies: `stop_after_attempt`, `stop_after_delay`, `stop_before_delay`, `stop_never`, `stop_any`,
  `stop_all` and the `|` and `&` operators, with all of their arguments;
- wait strategies: `wait_fixed`, `wait_none`, `wait_random`, `wait_incrementing`, `wait_exponential`,
  `wait_chain`, `wait_combine` and the `+` operator, with all of their arguments and defaults; time
  arguments may be numbers of seconds or `timedelta` objects;
- retry conditions: the default condition, `retry_always`, `retry_never`, `retry_if_exception`,
  `retry_if_exception_type`, `retry_if_not_exception_type`, `retry_if_result`, `retry_if_not_result`,
  `retry_if_exception_message`, `retry_any`, `retry_all` and the `|` and `&` operators, with all of their
  arguments, and raising `TryAgain`;
- giving up: `RetryError`, its `last_attempt` and `reraise()`;
- `RetryCallState` and its documented members (`retry_object`, `fn`, `args`, `kwargs`, `attempt_number`,
  `outcome`, `outcome_timestamp`, `idle_for`, `upcoming_sleep`, `next_action`, `start_time`,
  `seconds_since_start`, `prepare_for_next_attempt`, `set_result`, `set_exception`), and the `Future` objects it
  holds;
- the `statistics` dictionary and every key it documents.

Strategies are plain callables that take a `RetryCallState`: tests may build one themselves and call a strategy
directly, or observe strategies through `Retrying`. Pass your own `sleep` callable so that tests never really
sleep. Import from `tenacity`; do not import anything whose name begins with an underscore.

## Not part of the contract

The maintainers treat the following as unstable and do not want them
asserted:

- Error message text, and the `str()` and `repr()` of errors and objects. Exception classes: `RetryError` (or the
  configured `retry_error_cls`), `TryAgain` and exceptions raised by the retried function are part of the
  contract; for anything else assert that a call raises, not which exception class it raises. Arguments of
  undocumented types are outside the contract, and so are any incidental exceptions they cause.
- Asyncio, trio and tornado support, `AsyncRetrying` and coroutine callbacks; `wait_random_exponential`,
  `wait_full_jitter`, `wait_exponential_jitter`, `wait_exception`, `stop_when_event_set`,
  `retry_if_exception_cause_type`, `retry_unless_exception_type` and `retry_if_not_exception_message`; the logging
  helpers (`before_log`, `after_log`, `before_sleep_log`), the `name` option and `get_fn_name`.
- Any value read from the real clock (`start_time`, `outcome_timestamp`, `seconds_since_start` and the
  `start_time` and `delay_since_first_attempt` statistics as recorded by a real run), and anything else that
  depends on timing or machine speed. Exact values drawn from randomness.
- Static typing, tracebacks, line numbers, `__code__` objects and log output.

The documentation describes the intended behavior. Where the documentation
disagrees with itself or with the library's current observable behavior, or
where a docstring or an example is factually contradicted by the code's
observable behavior, current behavior governs: record expected values by
running the code as it is today rather than reasoning them out from the
documentation alone.

## Environment

The environment contains Python 3.13 with `pytest` 9.1.1; tenacity has no runtime dependencies. tenacity is
importable from `/app` (on `PYTHONPATH`). The repository's own `tests/` directory may be read for orientation but
is not available when the suite runs.

## Test hygiene and CI requirements

- Add files only under `/app/regression_tests/`. Changes to any other path
  are rejected. (Runtime side effects such as bytecode caches are not part of
  your change.)
- CI runs `pytest` on that directory alone, with no repository test
  configuration: the suite must be standalone (no conftest outside the
  directory, no network, no external services). It runs as an unprivileged
  user with a read-only test directory and a read-only copy of the library;
  scratch space is provided through `TMPDIR`, with `HOME` pointing at the same
  per-run directory.
- Test files must match `test_*.py` or `*_test.py` and test functions must
  start with `test_`.
- Do no library work at import or collection time: call the library inside
  test functions. A module that fails to import breaks CI.
- CI compares the collected test set across runs: never derive test lists,
  parametrize values, or ids from library output, randomness, the
  environment, or the filesystem.
- Tests MUST NOT depend on source file contents, file paths, environment
  values, process state, timing, or state left by earlier runs.
- The suite runs many times in CI; a full run, collection included, must
  finish in under 30 seconds.
- The suite must pass on the repository as it is today.
