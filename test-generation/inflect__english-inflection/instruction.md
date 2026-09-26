# Build a regression test suite for inflect's English inflection engine

The repository at `/app` is **inflect 7.5.0** (commit `c079a96`), a library that generates English plurals,
singular nouns, ordinals, indefinite articles and number words. The maintainers are about to refactor the
inflection engine in `inflect/__init__.py` and need a behavioral safety net for its documented public API
first: the noun, article, ordinal and number-word methods of `inflect.engine`. Your job is to write that
suite.

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

The documented observable behavior of the following methods of an `inflect.engine()` object with its
default settings, as described in the README and the docstrings:

- nouns: `plural` and `plural_noun` (`text`, `count`) and `singular_noun` (`text`, `count`, `gender`);
- indefinite articles: `a` and `an` (`text`, `count`);
- ordinals: `ordinal` (`num`);
- number words: `number_to_words` (`num`) with all of its documented options: `wantlist`, `group`, `comma`,
  `andword`, `zero`, `one`, `decimal` and `threshold`.

Import from `inflect`; do not import anything whose name begins with an underscore.

## Not part of the contract

The maintainers treat the following as unstable and do not want them
asserted:

- Error message text, and the `str()` and `repr()` of errors and objects. Exception classes: assert that a
  call raises, not which exception class it raises. Arguments of undocumented types are outside the contract,
  and so are any incidental exceptions they cause.
- Engine configuration and user definitions: `classical()`, `gender()`, `num()` and the `def*` methods.
  Create a fresh engine in each test.
- The other engine methods: `inflect()` templates, `compare*`, `join`, `no`, `present_participle`, and the
  verb and adjective methods (`plural_verb`, `plural_adj` and related helpers).
- Static typing, tracebacks, line numbers, `__code__` objects and log output.

The documentation describes the intended behavior. Where the documentation
disagrees with itself or with the library's current observable behavior, or
where a docstring or an example is factually contradicted by the code's
observable behavior, current behavior governs: record expected values by
running the code as it is today rather than reasoning them out from the
documentation alone.

## Environment

The environment contains Python 3.13 with `pytest` 9.1.1, plus the library's pinned runtime dependencies
more-itertools 11.1.0, typeguard 4.6.0 and typing_extensions 4.16.0. inflect is importable from `/app` (the
directory is on `PYTHONPATH`). The repository's own `tests/` directory may be read for orientation but is not
available when the suite runs.

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
