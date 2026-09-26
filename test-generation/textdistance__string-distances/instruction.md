# Build a regression test suite for textdistance's string distance algorithms

The repository at `/app` is **textdistance 4.6.3** (commit `faa25f6`), a pure-Python library that computes
distances and similarities between sequences with many algorithms behind one common interface. The
maintainers are about to refactor `textdistance/algorithms/` and need a behavioral safety net for the
documented public API of a set of its algorithms first: the edit-based, token-based, sequence-based and
simple algorithms listed below. Your job is to write that suite.

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

The documented observable behavior of the pure-Python implementations of the following, as described in the
README and the class docstrings, used through the ready-made instances or through the classes:

- `hamming` / `Hamming`, `levenshtein` / `Levenshtein`, `damerau_levenshtein` / `DamerauLevenshtein`,
  `jaro` / `Jaro`, `jaro_winkler` / `JaroWinkler`, `jaccard` / `Jaccard`, `lcsseq` / `LCSSeq`, and
  `prefix` / `Prefix` and `postfix` / `Postfix`;
- all documented constructor options of those classes: `qval`, `test_func`, `truncate`, `restricted`,
  `long_tolerance`, `winklerize`, `as_set`, `sim_test` and `external`;
- for each algorithm, the whole common interface: calling the instance, `distance`, `similarity`,
  `normalized_distance`, `normalized_similarity` and `maximum`.

Import from `textdistance`; do not import anything whose name begins with an underscore.

## Not part of the contract

The maintainers treat the following as unstable and do not want them
asserted:

- Error message text, and the `str()` and `repr()` of errors and objects. Exception classes: assert that a
  call raises, not which exception class it raises. Arguments of undocumented types are outside the contract,
  and so are any incidental exceptions they cause.
- All other algorithms (other edit-based, token-based and sequence-based ones, and the compression-based and
  phonetic families), the benchmark module and the package version string.
- Optional external libraries: none are installed, so the pure-Python code always runs; which external
  library would be chosen when one is installed is not part of the contract.
- Floating point results beyond ordinary rounding: compare non-integer results approximately.
- Static typing, tracebacks, line numbers, `__code__` objects and log output.

The documentation describes the intended behavior. Where the documentation
disagrees with itself or with the library's current observable behavior, or
where a docstring or an example is factually contradicted by the code's
observable behavior, current behavior governs: record expected values by
running the code as it is today rather than reasoning them out from the
documentation alone.

## Environment

The environment contains Python 3.13 with `pytest` 9.1.1; textdistance has no required runtime dependencies
and none of its optional extras (numpy or the external libraries) are installed. textdistance is importable
from `/app` (the directory is on `PYTHONPATH`). The repository's own `tests/` directory may be read for
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
