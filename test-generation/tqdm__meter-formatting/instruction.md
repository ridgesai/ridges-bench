# Build a regression test suite for tqdm's meter formatting helpers

The repository at `/app` is **tqdm 4.70.1** (commit `9cf5a12`), a library that draws progress bars for
Python loops and command-line tools. The maintainers are about to refactor the text formatting code in
`tqdm/std.py` that turns progress numbers into meter strings, and need a behavioral safety net for its
documented public API first: the static formatting helpers of the `tqdm.tqdm` class. Your job is to write
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

The documented observable behavior of the following, as described in the docstrings of `tqdm/std.py` and the
README, called directly on the class (no progress bar object is needed):

- `tqdm.format_sizeof(num, suffix, divisor)`, `tqdm.format_interval(t)` and `tqdm.format_num(n)`;
- `tqdm.format_meter(n, total, elapsed, ...)` with all of its documented parameters: `n`, `total`, `elapsed`,
  `ncols`, `prefix`, `ascii`, `unit`, `unit_scale`, `rate`, `bar_format`, `postfix`, `unit_divisor` and
  `initial`;
- the `bar_format` template language: every variable the docstring lists (`l_bar`, `bar`, `r_bar`, `n`,
  `n_fmt`, `total`, `total_fmt`, `percentage`, `elapsed`, `elapsed_s`, `ncols`, `nrows`, `desc`, `unit`,
  `rate`, `rate_fmt`, `rate_noinv`, `rate_noinv_fmt`, `rate_inv`, `rate_inv_fmt`, `postfix`, `unit_divisor`,
  `remaining` and `remaining_s`) and the documented `bar_format` syntax.

Import from `tqdm`; do not import anything whose name begins with an underscore.

## Not part of the contract

The maintainers treat the following as unstable and do not want them
asserted:

- Error message text, and the `str()` and `repr()` of errors and objects. Exception classes: assert that a
  call raises, not which exception class it raises. Arguments of undocumented types are outside the contract,
  and so are any incidental exceptions they cause.
- Creating, updating or displaying `tqdm` progress bars, and everything that depends on the terminal, threads,
  the current time or the platform: the `eta` variable, the `colour` parameter and terminal width detection.
- The `contrib`, notebook, GUI, CLI and other integration modules.
- Static typing, tracebacks, line numbers, `__code__` objects and log output.

The documentation describes the intended behavior. Where the documentation
disagrees with itself or with the library's current observable behavior, or
where a docstring or an example is factually contradicted by the code's
observable behavior, current behavior governs: record expected values by
running the code as it is today rather than reasoning them out from the
documentation alone.

## Environment

The environment contains Python 3.13 with `pytest` 9.1.1; tqdm has no runtime dependencies on Linux. tqdm is
importable from `/app` (the directory is on `PYTHONPATH`). The repository's own `tests/` directory may be read
for orientation but is not available when the suite runs.

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
