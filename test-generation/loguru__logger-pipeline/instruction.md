# Build a regression test suite for loguru's logger pipeline

The repository at `/app` is **loguru 0.7.3** (commit `ae3bfd1`), a logging library built around a single
pre-configured `logger` object to which sinks are added. The maintainers are about to refactor
`loguru/_logger.py`, `loguru/_handler.py`, `loguru/_filters.py`, `loguru/_colorizer.py` and the other modules a
log call passes through, and need a behavioral safety net for its documented public API first: adding and
removing handlers, the logging methods, levels, formats, filters, context and `opt`/`catch`. Your job is to write
that suite.

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

The documented observable behavior of the `from loguru import logger` object, as described in `README.md`, the
documentation under `docs/` and the docstrings, observed through sinks your tests supply (a callable receiving
each formatted message, whose `.record` attribute holds the record dict, or an `io.StringIO`), always added with
`colorize=False`:

- `logger.add` with its options `sink`, `level`, `format`, `filter` and `colorize`, and `logger.remove`, including
  the handler ids they use;
- the logging methods `trace`, `debug`, `info`, `success`, `warning`, `error`, `critical`, `exception` and `log`,
  and message formatting with positional and keyword arguments;
- levels: the built-in levels and `logger.level(name, no=None, color=None, icon=None)` to create, update and look
  up levels, and the level objects it returns;
- `format` given as a string or a callable, every record field documented for it (`exception`, `extra`, `file`,
  `function`, `level`, `line`, `message`, `module`, `name`, `process`, `thread` and their attributes), format
  specs, and every documented form of color markup tag in formats, messages and level colors;
- `filter` given as `None`, a string, a dict or a callable, in every form the documentation describes;
- `logger.bind`, `logger.contextualize` and `logger.patch`;
- `logger.opt` with all of its options: `exception`, `record`, `lazy`, `colors`, `raw`, `capture` and `depth`;
- `logger.catch` as a decorator and as a context manager, with all of its options: `exception`, `level`,
  `reraise`, `onerror`, `exclude`, `default` and `message`.

Tests share one global `logger`: each test must remove every handler it adds (for example with an autouse fixture
calling `logger.remove()`), and custom level names should be unique per test. Import only `loguru.logger`.

## Not part of the contract

The maintainers treat the following as unstable and do not want them
asserted:

- Error message text, and the `str()` and `repr()` of errors and objects. Exception classes: assert that a call raises,
  not which exception class it raises. Arguments of undocumented types
  are outside the contract, and so are any incidental exceptions they cause.
- File sinks and their options (rotation, retention, compression), `serialize`, `enqueue`, `context`,
  `backtrace`, `diagnose` and the `catch` option of `add`, coroutine sinks, standard `logging` handlers,
  `configure`, `enable`/`disable`, `parse` and multiprocessing.
- Colored (ANSI) output and anything else that depends on the terminal or platform; the process and thread ids
  and names; `{time}`, `{elapsed}` and anything else that depends on time (use formats without them).
- The exact text of tracebacks and of the default format and default `catch` message.
- Static typing, tracebacks, line numbers, `__code__` objects and log output other than what your own sinks
  receive.

The documentation describes the intended behavior. Where the documentation
disagrees with itself or with the library's current observable behavior, or
where a docstring or an example is factually contradicted by the code's
observable behavior, current behavior governs: record expected values by
running the code as it is today rather than reasoning them out from the
documentation alone.

## Environment

The environment contains Python 3.13 with `pytest` 9.1.1; loguru has no third-party runtime dependencies on
Linux. loguru is importable from `/app` (on `PYTHONPATH`). The repository's own `tests/` directory may be read for
orientation but is not available when the suite runs.

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
