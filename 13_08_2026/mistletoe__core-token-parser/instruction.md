# Reduce complexity in mistletoe's core span tokenizer

`mistletoe/core_tokens.py` contains two functions above a cyclomatic
complexity ceiling of 10. Bring this exact command to zero findings:

```bash
ruff check --isolated --select C901 \
  --config 'lint.mccabe.max-complexity=10' mistletoe/core_tokens.py
```

At the pinned revision Ruff reports `find_core_tokens` at 14 and
`match_link_dest` at 17. This is a behavior-preserving parser refactor, not a
Markdown syntax change.

Requirements:

- Preserve link, image, emphasis, code-span, escape, whitespace, control
  character, angle-destination, and nested-parenthesis behavior.
- Preserve match boundaries and destination text, not just rendered happy
  paths. Callers use these offsets to construct tokens.
- Keep the file's stateful delimiter behavior intact: image markers and link
  delimiters can be separated, escaped, abandoned, or nested.
- Refactor in `mistletoe/core_tokens.py`. Do not suppress Ruff, move or rename
  existing public definitions, export complexity to another file, or add
  dependencies. New private helpers in this file are welcome.
