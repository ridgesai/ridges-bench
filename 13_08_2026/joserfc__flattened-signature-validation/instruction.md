# Replace an unsafe assertion in flattened JWS verification

`src/joserfc/_rfc7515/json.py` currently has one `S101` finding. Bring this
exact command to zero findings:

```bash
ruff check --isolated --select S101 src/joserfc/_rfc7515/json.py
```

The assertion guards a flattened JSON Web Signature object's optional
signature immediately before verification. Assertions disappear under
`python -O`; malformed cryptographic input must have the same result regardless
of interpreter optimization.

Requirements:

- A flattened object with no signature is not valid and must produce the same
  negative verification result used by the general-JSON path when it has no
  signatures.
- Do not invoke key lookup or algorithm verification when the signature is
  absent.
- Preserve verification of valid signatures and rejection of bad signatures.
- Make the real fix in `src/joserfc/_rfc7515/json.py`. Do not suppress Ruff,
  rename or remove existing definitions, or add dependencies.
