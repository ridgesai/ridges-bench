# Reduce SMTP configuration and message-preparation complexity

`src/aiosmtplib/smtp.py` contains two methods above a cyclomatic complexity
ceiling of 12. Bring this exact command to zero findings:

```bash
ruff check --isolated --select C901 \
  --config 'lint.mccabe.max-complexity=12' src/aiosmtplib/smtp.py
```

At the pinned revision Ruff reports `_update_settings_from_kwargs` at 17 and
`send_message` at 14. This is a behavior-preserving refactor of configuration
updates and email-envelope preparation, not a change to the SMTP API.

Requirements:

- Preserve the distinction between omitted `Default.token` settings, the
  options for which `None` means "leave unchanged", and options for which an
  explicit `None` clears a stored value.
- Preserve sender and recipient inference, explicit string and sequence
  recipients, empty/missing-header errors, Bcc envelope handling and Bcc
  header removal from transmitted bytes.
- Reject missing or invalid envelope inputs before performing EHLO/HELO or any
  other network-facing negotiation, as the pinned implementation does.
- Preserve SMTPUTF8/8BITMIME negotiation, caller-supplied mail options,
  serialization policy, timeout forwarding, and `sendmail` return values.
- Do not mutate caller-owned message or option inputs beyond the behavior of
  the existing implementation.
- Refactor only `src/aiosmtplib/smtp.py`. Do not suppress Ruff, move or rename
  existing definitions, export complexity to another file, or add
  dependencies. New private helpers in this file are welcome.
