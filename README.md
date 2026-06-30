# ridges-bench

```
         _                                       _
    _  _ | |                                     | | _  _
   | || || |                                     | || || |
 =H| || || |=====================================| || || |H=
   |_||_|| |                                     | ||_||_|
         |_|                                     |_|
 
```

Synthetic SWE task **samples** for Ridges — a small set of synthetic
coding tasks miners can run their agent against locally to iterate, debug,
and finetuning.

Please do not infer the difficulty of what you will in the actual 
competition from these tasks.

> These are **samples**, they will not be used for evaluations nor their source will be used.

Samples are grouped by the date they were released (e.g. `30_06_2026/`).

Each directory is one Harbor task - same format that the subnet works on.

```
<task-name>/
├── instruction.md     # the problem statement handed to your agent
├── task.toml          # task metadata (difficulty, timeouts, environment)
├── environment/       # the container/env the task runs in
├── tests/             # verifier tests that decide pass/fail (your score)
└── solution/          # the gold patch — reference only, not used when your agent runs
```

## Run a task with the Ridges CLI

You need the `ridges` CLI installed (from the ridges repo https://github.com/ridgesai/ridges) and an OpenRouter API key.

1. One-time setup:
   ```bash
   ridges miner setup
   ```
   This configures your workspace, agent, and provider. Put your OpenRouter key in `.env.miner`:
   ```
   RIDGES_OPENROUTER_API_KEY=sk-or-...
   ```
   The provider must be configured, or `run-local` will error.

2. Run your agent against a single task:
   ```bash
   ridges miner run-local --task-path ./30_06_2026/<task-name>
   ```

   You'll see the reward and per-test results:
   ```
   SUCCEEDED
   reward: 1.0
   tests: 12 total (12 passed, 0 failed, 0 skipped)
   ```

> Local mode runs your agent + verifier but does **not** enforce the platform's
> sandbox/budget restrictions — it's for iteration, not official scoring.

## Your agent

A miner agent is a single `agent.py` exposing:

```python
def agent_main(input: dict) -> str:
    # return a unified-diff patch string
    ...
```
