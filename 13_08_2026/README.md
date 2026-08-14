# Public miner tasks

These eight tasks are public development and calibration examples. Each task
includes a reference solution for after-the-fact inspection.

Run a task locally from the `ridges-bench` repository root after configuring
the Ridges miner CLI:

```bash
ridges miner setup
ridges miner run-local \
  --task-path "./13_08_2026/pyatv__file-storage-nonblocking" \
  --agent-path "/path/to/your/agent"
```

Available tasks:

| Task | Ruff rule | Focus |
|---|---|---|
| `pyatv__file-storage-nonblocking` | ASYNC240 | Non-blocking async file storage |
| `sqlite-utils__rows-file-error-chaining` | B904 | Exception chaining and public error translation |
| `mistletoe__core-token-parser` | C901 | Markdown tokenizer complexity |
| `joserfc__flattened-signature-validation` | S101 | Runtime validation without assertions |
| `arq__completion-driven-shutdown` | ASYNC110 | Completion-driven async shutdown |
| `procrastinate__job-abort-attribution` | B023 | Per-job callback binding |
| `aiosmtplib__smtp-message-preparation` | C901 | SMTP configuration and envelope preparation |
| `aiomisc__worker-socket-isolation` | S306 | Secure Unix-socket lifecycle |

Tasks are samples - real competition will not reuse the same strategy, task/repo family etc. 
