# Build a regression test suite for boltons' iterutils helpers

The repository at `/app` is **boltons 26.2.0** (commit `4332b35`), a collection of pure-Python utilities that
complement the standard library. The maintainers are about to refactor `boltons/iterutils.py` and need a
behavioral safety net for its documented public API first: the chunking, windowing, grouping, splitting,
stripping, selection, flattening, backoff and nested-data helpers. Your job is to write that suite.

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

The documented observable behavior of the following functions of `boltons.iterutils`, as described in their
docstrings and in `docs/iterutils.rst`, with all of their documented arguments and every accepted form of each
argument:

- chunks and windows: `chunked` and `chunked_iter` (`size`, `count`, `fill`), `windowed` and `windowed_iter`
  (`size`, `fill`), `pairwise` and `pairwise_iter` (`end`);
- grouping and deduplication: `bucketize` (`key`, `value_transform`, `key_filter`), `partition` (`key`, `*keys`),
  `unique` and `unique_iter` (`key`), `redundant` (`key`, `groups`);
- splitting and stripping: `split` and `split_iter` (`sep`, `maxsplit`), `strip`, `lstrip`, `rstrip`,
  `strip_iter`, `lstrip_iter` and `rstrip_iter` (`strip_value`);
- selection: `first` and `one` (`default`, `key`), `same` (`ref`);
- flattening: `flatten` and `flatten_iter`;
- backoff sequences: `backoff` and `backoff_iter` (`start`, `stop`, `count`, `factor`, `jitter`);
- nested data: `remap` (`visit`, `enter`, `exit`, `cache`, `reraise_visit`) together with `default_visit`,
  `default_enter` and `default_exit`, `get_path` (`path`, `default`) and `PathAccessError`, and `research`
  (`query`, `reraise`, `enter`).

Import from `boltons.iterutils`; do not import anything whose name begins with an underscore.

## Not part of the contract

The maintainers treat the following as unstable and do not want them
asserted:

- Error message text, and the `str()` and `repr()` of errors and objects. Exception classes are part of the
  contract for the functions in scope: the exception classes each function raises today for invalid arguments or
  failed lookups. Arguments of undocumented types are outside the contract, and so are any
  incidental exceptions they cause.
- The other `iterutils` helpers (`chunk_ranges`, `frange`, `xfrange`, `soft_sorted`, `untyped_sorted`, the GUID
  iterators, `is_iterable`, `is_scalar`, `is_collection`) and every other boltons module; the `trace` option of
  `remap` and anything printed; exact values produced with `jitter`, since they depend on
  randomness.
- Static typing, tracebacks, line numbers, `__code__` objects and log output.

The documentation describes the intended behavior. Where the documentation
disagrees with itself or with the library's current observable behavior, or
where a docstring or an example is factually contradicted by the code's
observable behavior, current behavior governs: record expected values by
running the code as it is today rather than reasoning them out from the
documentation alone.

## Environment

The environment contains Python 3.13 with `pytest` 9.1.1; boltons has no runtime dependencies. boltons is
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
