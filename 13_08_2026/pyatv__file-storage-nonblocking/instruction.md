# Keep pyatv file storage from blocking the event loop

`pyatv/storage/file_storage.py` currently has one `ASYNC240` finding. Bring
this exact command to zero findings:

```bash
ruff check --isolated --select ASYNC240 pyatv/storage/file_storage.py
```

`FileStorage.load()` is asynchronous, but its existence check currently runs
on the event-loop thread. A slow or remote filesystem can therefore stall
unrelated coroutines before the file read is offloaded.

Requirements:

- Keep filesystem work off the event-loop thread, including the existence
  lookup.
- A missing file remains a no-op.
- Existing JSON is loaded exactly as before, including validation and the hash
  being based on the raw data read from disk.
- Parsing, validation, and I/O failures must not be silently swallowed.
- Make the real fix in `pyatv/storage/file_storage.py`. Do not suppress Ruff,
  de-async the API, rename or remove existing definitions, or add dependencies.
