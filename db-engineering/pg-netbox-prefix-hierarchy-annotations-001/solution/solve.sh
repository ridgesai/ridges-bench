#!/bin/bash
set -euo pipefail

cd /app
python - <<'PY'
from pathlib import Path

path = Path('netbox/ipam/querysets.py')
text = path.read_text()
anchor = """        return self.annotate(
            hierarchy_depth=RawSQL('0', ()),
            hierarchy_children=RawSQL('0', ()),
        )
"""
replacement = """        return self.annotate(
            hierarchy_depth=RawSQL(
                'SELECT COUNT(DISTINCT U0."prefix") AS "c" '
                'FROM "ipam_prefix" U0 '
                'WHERE (U0."prefix" >> "ipam_prefix"."prefix" '
                'AND COALESCE(U0."vrf_id", 0) = COALESCE("ipam_prefix"."vrf_id", 0))',
                ()
            ),
            hierarchy_children=RawSQL(
                'SELECT COUNT(U1."prefix") AS "c" '
                'FROM "ipam_prefix" U1 '
                'WHERE (U1."prefix" << "ipam_prefix"."prefix" '
                'AND COALESCE(U1."vrf_id", 0) = COALESCE("ipam_prefix"."vrf_id", 0))',
                ()
            )
        )
"""
if text.count(anchor) != 1:
    raise SystemExit('frozen hierarchy placeholder anchor changed')
path.write_text(text.replace(anchor, replacement, 1))
PY

ruff check --no-cache netbox/ipam/querysets.py
