# Replace polling in arq's worker shutdown path

`arq/worker.py` polls at a fixed interval while waiting for active jobs to
finish. Bring this exact Ruff command to zero findings:

```bash
ruff check --isolated --select ASYNC110 arq/worker.py
```

At the pinned revision Ruff reports one `ASYNC110` finding in
`Worker._sleep_until_tasks_complete`. Replace that polling loop with
completion-driven asynchronous waiting while preserving arq's shutdown
semantics.

Requirements:

- The live `Worker.tasks` mapping remains authoritative. Jobs added while
  shutdown is already waiting must also be awaited.
- Return only after the mapping has been drained by the worker's normal job
  cleanup path, including the interval after a task finishes but before its
  entry is removed.
- Cancelling the shutdown waiter must not cancel the jobs it is observing.
- Preserve prompt behavior when there are no active jobs and avoid a fixed
  sleep interval while unfinished jobs exist.
- Refactor only `arq/worker.py`. Do not suppress Ruff, move or rename existing
  definitions, export the work to another file, or add dependencies.
