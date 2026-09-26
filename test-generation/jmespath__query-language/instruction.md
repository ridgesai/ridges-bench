# Build a regression test suite for jmespath's query language

The repository at `/app` is **jmespath 1.1.0** (commit `6ff419a`), the Python implementation of JMESPath, a
query language for extracting and reshaping JSON-like data. The maintainers are about to refactor
`jmespath/lexer.py`, `jmespath/parser.py`, `jmespath/visitor.py` and `jmespath/functions.py` and need a behavioral
safety net for its documented public API first: `jmespath.search`, `jmespath.compile`, `jmespath.Options`, custom
functions and the exceptions module. Your job is to write that suite.

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

The documented observable behavior of the following, as described in `README.rst`, the docstrings and the
JMESPath specification that the library implements:

- the entry points: `jmespath.search(expression, data, options=None)` and `jmespath.compile(expression)` followed
  by `.search(data, options=None)`, and `jmespath.Options` with all of its arguments (`dict_cls`,
  `custom_functions`);
- the whole expression grammar: identifiers (unquoted and quoted), sub-expressions, index expressions, slices,
  list, slice, object, flatten and filter projections, multiselect lists and hashes, pipes, the comparators
  (`==`, `!=`, `<`, `<=`, `>`, `>=`), `||`, `&&`, `!`, parentheses, JSON literals, raw string literals, the
  current node `@` and expression references (`&`), with the semantics the JMESPath specification defines;
- every built-in function (`abs`, `avg`, `ceil`, `contains`, `ends_with`, `floor`, `join`, `keys`, `length`,
  `map`, `max`, `max_by`, `merge`, `min`, `min_by`, `not_null`, `reverse`, `sort`, `sort_by`, `starts_with`,
  `sum`, `to_array`, `to_number`, `to_string`, `type`, `values`), with their documented signatures;
- custom functions: subclassing `jmespath.functions.Functions`, declaring `_func_<name>` methods with the
  `jmespath.functions.signature` decorator, and passing an instance through `Options(custom_functions=...)`;
- `jmespath.exceptions` and which of its classes is raised for invalid expressions and invalid function calls.

Import from `jmespath`, `jmespath.functions` and `jmespath.exceptions`; apart from the documented `_func_<name>`
method naming convention, do not import or use anything whose name begins with an underscore.

## Not part of the contract

The maintainers treat the following as unstable and do not want them
asserted:

- Error message text, and the `str()` and `repr()` of errors and objects. Exception classes from
  `jmespath.exceptions` are part of the contract; for other errors assert that a call raises, not which exception
  class it raises. The position and token details carried by exceptions are not part of the contract. Arguments
  of undocumented types are outside the contract, and so are any incidental exceptions they cause.
- The parser's internal expression cache, the parsed tree returned by `compile`, the `jp.py` command-line script
  and the Graphviz output of parsed expressions; deprecated syntax that emits warnings; the iteration order of `keys`, `values` and object projections beyond what the input
  dict defines.
- Static typing, tracebacks, line numbers, `__code__` objects and log output.

The documentation describes the intended behavior. Where the documentation
disagrees with itself or with the library's current observable behavior, or
where a docstring or an example is factually contradicted by the code's
observable behavior, current behavior governs: record expected values by
running the code as it is today rather than reasoning them out from the
documentation alone.

## Environment

The environment contains Python 3.13 with `pytest` 9.1.1; jmespath has no third-party runtime dependencies.
jmespath is importable from `/app` (on `PYTHONPATH`). The repository's own `tests/` directory may be read for
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
