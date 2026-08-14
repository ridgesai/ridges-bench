# Secure aiomisc's worker-pool Unix socket

`aiomisc/worker_pool.py` creates a predictable pathname in a shared temporary
directory before binding its privileged worker-control socket. Bring this
exact Ruff command to zero findings:

```bash
ruff check --isolated --select S306 aiomisc/worker_pool.py
```

At the pinned revision Ruff reports one insecure temporary-name finding. A
cosmetic random-name replacement is not sufficient: the pathname must not be
claimable by another local process between name selection and bind.

Requirements:

- On Unix, create the socket inside a securely created, owner-only filesystem
  namespace and retain owner-only permissions on the socket itself.
- Keep the namespace alive for the full worker-pool lifetime, and remove both
  the socket and its private namespace during normal close and failed setup.
- Preserve supervisor startup, authentication, task execution, cancellation,
  and idempotent cleanup behavior. Keep the non-Unix fallback working.
- Refactor only `aiomisc/worker_pool.py`. Do not suppress Ruff, move or rename
  existing definitions, export the work to another file, or add dependencies.
