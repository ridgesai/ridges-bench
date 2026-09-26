# Test generation samples

These ten tasks are public development and calibration examples for the
test generation category. Each task includes a reference solution for
after-the-fact inspection.

In this category an agent writes a regression test suite for part of a Python
repository at a fixed version. The suite is graded by running it against the
code as it is, against copies with small behavioral bugs introduced,
and against copies rewritten without changing behavior. The reward is
1 only if the suite passes on the original code and on every decoy, and fails
on every mutant. There is no partial credit.

Run a task locally from the `ridges-bench` repository root after configuring
the Ridges miner CLI:

```bash
ridges miner setup
ridges miner run-local \
  --task-path "./test-generation/natsort__natural-ordering" \
  --agent-path "/path/to/your/agent"
```

The verifier report lists one row per copy (`original_passes`,
`decoy_N_passes`, `mutant_N_caught`), so you can see which injected bugs your
agent's suite missed.

Available tasks:

| Task | Library | Focus | Difficulty |
|---|---|---|---|
| `boltons__iterutils` | boltons | The `iterutils` module | easy |
| `inflect__english-inflection` | inflect | Plurals, singulars, articles, ordinals and number words | easy |
| `jmespath__query-language` | jmespath | The JMESPath query language | hard |
| `loguru__logger-pipeline` | loguru | The logger pipeline | hard |
| `natsort__natural-ordering` | natsort | Natural sorting functions and `ns` flags | easy |
| `python-slugify__slug-options` | python-slugify | The `slugify()` algorithm and its options | hard |
| `tenacity__retry-strategies` | tenacity | Retry, stop and wait strategies | hard |
| `textdistance__string-distances` | textdistance | String distance algorithms | easy |
| `toolz__dict-helpers` | toolz | Dictionary helpers | easy |
| `tqdm__meter-formatting` | tqdm | Meter formatting helpers | easy |

Difficulty labels reflect how two reference agents did on these samples, not
the difficulty of the real competition.

What to take from these samples, and what not to:

- A strong suite pins down observable behavior, including edge and boundary
  cases, and only through the public API the task names. Each instruction
  defines what is in and out of the contract; asserting on anything it
  excludes (private names, exact error messages, incidental ordering) makes a
  suite fail on behavior-preserving rewrites.
- Suites must be deterministic and self-contained: they run as an
  unprivileged user, with a per-run scratch directory, and many times over.
- Read the repository's documentation and source at that version to learn its
  behavior; record expected values by running the code as it is today.
- Suites that inspect the code's source, fingerprint files, or probe the
  grading environment do not work: decoys change the source without changing
  behavior, and the grading environment is not visible to the suite.
- This page explains grading so you can build for it, but your agent's prompts
  and code should describe the task, not how it is graded: catch any change in
  the covered behavior, and keep passing when the code is refactored without
  changing behavior.
- The rule of thumb: the agent you submit should write good regression suites
  for Python repositories it has never seen. Specializing on test design is the
  point. Knowledge of specific tasks, repositories, bugs, or verifiers is not.

Tasks are samples - real competition will not reuse the same repositories,
bug selection, task counts or grading details.
