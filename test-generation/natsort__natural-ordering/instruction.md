# Build a regression test suite for natsort's natural ordering API

The repository at `/app` is **natsort 8.4.0** (commit `d9503c0`), a library that sorts strings containing
numbers the way a human would (`item2` before `item10`). The maintainers are about to refactor the sort key
machinery in `natsort/natsort.py` and `natsort/utils.py` and need a behavioral safety net for its documented
public API first: the sorting functions, the key generators, the helper functions and the `ns` flags. Your
job is to write that suite.

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

The documented observable behavior of the following, as described in the README and the API documentation
(`docs/api.rst` and the docstrings):

- `natsorted`, `humansorted` and `realsorted`, and `index_natsorted`, `index_humansorted` and
  `index_realsorted`, with all of their documented arguments (`key`, `reverse` and `alg`);
- `order_by_index`, `natsort_keygen` (`key` and `alg`) and `natsort_key`, judged by the order their keys
  produce;
- the helper functions `decoder`, `as_ascii`, `as_utf8` and `chain_functions`;
- the whole `ns` enum, alone and in combination: `DEFAULT`, `INT`, `UNSIGNED`, `FLOAT`, `SIGNED`, `REAL`,
  `NOEXP`, `PATH`, `LOCALEALPHA`, `LOCALENUM`, `LOCALE`, `IGNORECASE`, `LOWERCASEFIRST`, `GROUPLETTERS`,
  `UNGROUPLETTERS`, `CAPITALFIRST`, `NANLAST`, `COMPATIBILITYNORMALIZE`, `NUMAFTER` and `PRESORT`.

Every documented short alias of these `ns` members is in scope as well.

Import from `natsort`; do not import anything whose name begins with an underscore.

## Not part of the contract

The maintainers treat the following as unstable and do not want them
asserted:

- Error message text, and the `str()` and `repr()` of errors and objects. Exception classes: assert that a
  call raises, not which exception class it raises. Arguments of undocumented types are outside the contract,
  and so are any incidental exceptions they cause.
- The exact structure and contents of sort keys: assert on the order they produce, not on their values.
- The pattern text returned by `numeric_regex_chooser`.
- Locale-dependent results.
- `os_sorted`, `os_sort_key`, `os_sort_keygen` and the `natsort` command line tool.
- Static typing, tracebacks, line numbers, `__code__` objects and log output.

The documentation describes the intended behavior. Where the documentation
disagrees with itself or with the library's current observable behavior, or
where a docstring or an example is factually contradicted by the code's
observable behavior, current behavior governs: record expected values by
running the code as it is today rather than reasoning them out from the
documentation alone.

## Environment

The environment contains Python 3.13 with `pytest` 9.1.1; natsort has no runtime dependencies. The optional
fastnumbers and PyICU are not installed, and the suite runs in the default `C.UTF-8` locale. natsort is
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
