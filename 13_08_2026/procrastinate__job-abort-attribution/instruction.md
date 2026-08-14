# Preserve per-job abort attribution in procrastinate

`procrastinate/worker.py` constructs an abort-reason callback inside an
asynchronous job-fetch loop. Bring this exact Ruff command to zero findings:

```bash
ruff check --isolated --select B023 procrastinate/worker.py
```

At the pinned revision Ruff reports two references in the same callback. The
warning exposes a real late-binding bug: callbacks retained by concurrently
running jobs can consult the ID from a later loop iteration.

Requirements:

- Every job context must continue consulting the abort reason for that job's
  own ID, even after more jobs have been fetched.
- The callback must remain live: changes to the worker's abort-reason mapping
  after context creation must be visible when the callback is invoked.
- Missing and removed entries must still report no abort reason.
- Preserve worker concurrency, context contents, and job-processing behavior.
- Refactor only `procrastinate/worker.py`. Do not suppress Ruff, move or rename
  existing definitions, export the work to another file, or add dependencies.
