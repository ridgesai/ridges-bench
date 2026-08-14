# Make rows_from_file's error translation explicit

`sqlite_utils/utils.py` currently has one `B904` finding. Bring this exact
command to zero findings:

```bash
ruff check --isolated --select B904 sqlite_utils/utils.py
```

The finding is in `rows_from_file()`. When format detection receives a text
stream instead of the documented peekable binary stream, the function
translates an internal `AttributeError` into its public `TypeError` with a
useful explanation.

Requirements:

- Preserve the public `TypeError` type and message.
- Do not expose the implementation-detail `AttributeError` as the explicit
  cause of that public usage error or show it as an error in the handler.
- Keep valid CSV, TSV, JSON, and automatic format detection behavior intact.
- Make the real fix in `sqlite_utils/utils.py`. Do not suppress Ruff, move the
  raise elsewhere merely to hide it, rename or remove existing definitions,
  or add dependencies.
