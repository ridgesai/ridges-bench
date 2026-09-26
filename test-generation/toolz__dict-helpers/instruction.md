# Build a regression test suite for toolz's dictionary helpers

The repository at `/app` is **toolz 1.1.0** (commit `568c2b8`), a pure-Python library of functional
utilities for iterators, functions and dictionaries. The maintainers are about to refactor
`toolz/dicttoolz.py` and need a behavioral safety net for its documented public API first: the dictionary
helpers. Your job is to write that suite.

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

The documented observable behavior of the following, as described in their docstrings and the toolz
documentation:

- every function in `toolz.dicttoolz.__all__`: `merge`, `merge_with`, `valmap`, `keymap`, `itemmap`,
  `valfilter`, `keyfilter`, `itemfilter`, `assoc`, `dissoc`, `assoc_in`, `update_in` and `get_in`;
- all of their documented arguments and options: the accepted forms of the dictionary arguments, `func`,
  `predicate`, `key`, `keys`, `value`, `default`, `no_default` and `factory`.

Import from `toolz` or `toolz.dicttoolz`; do not import anything whose name begins with an underscore.

## Not part of the contract

The maintainers treat the following as unstable and do not want them
asserted:

- Error message text, and the `str()` and `repr()` of errors and objects. Exception classes: where a
  docstring names the exception class a function raises, that class is part of the contract; elsewhere
  assert that a call raises, not which exception class it raises. Arguments of undocumented types are
  outside the contract, and so are any incidental exceptions they cause.
- The rest of toolz: the iterator helpers in `toolz.itertoolz`, `functoolz`, `recipes`, the `curried` and
  `sandbox` namespaces, the `tlz` package and the package version string. The optional compiled `cytoolz`
  package is not installed.
- Static typing, tracebacks, line numbers, `__code__` objects and log output.

The documentation describes the intended behavior. Where the documentation
disagrees with itself or with the library's current observable behavior, or
where a docstring or an example is factually contradicted by the code's
observable behavior, current behavior governs: record expected values by
running the code as it is today rather than reasoning them out from the
documentation alone.

## Environment

The environment contains Python 3.13 with `pytest` 9.1.1; toolz has no runtime dependencies. toolz is
importable from `/app` (the directory is on `PYTHONPATH`). The repository's own `toolz/tests/` directory may
be read for orientation but is not available when the suite runs.

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
