#!/bin/bash
set -euo pipefail

cd /app
python3 - <<'PY'
from pathlib import Path

path = Path('netbox/extras/migrations/0107_cachedvalue_extras_cachedvalue_object.py')
data = path.read_text()
anchor = "fields=['object_type']"
replacement = "fields=['object_type', 'object_id']"
if data.count(anchor) != 1:
    raise SystemExit('frozen cached-value index migration changed')
path.write_text(data.replace(anchor, replacement, 1))
PY

ruff check --no-cache netbox/extras/migrations/0107_cachedvalue_extras_cachedvalue_object.py
