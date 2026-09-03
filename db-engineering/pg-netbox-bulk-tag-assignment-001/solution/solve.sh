#!/bin/bash
set -euo pipefail

cd /app
python - <<'PY'
from pathlib import Path

path = Path('netbox/extras/managers.py')
text = path.read_text()
anchor = '''        # Insert each relationship independently.
        for tag in tag_objs:
            if tag.pk in new_ids:
                self.through._default_manager.using(db).get_or_create(
                    tag=tag,
                    defaults=through_defaults or {},
                    **lookup,
                )
'''
replacement = '''        # Insert every new relationship in one statement.
        self.through._default_manager.using(db).bulk_create(
            [
                self.through(tag=tag, **lookup, **(through_defaults or {}))
                for tag in tag_objs
                if tag.pk in new_ids
            ],
            ignore_conflicts=True,
        )
'''
if text.count(anchor) != 1:
    raise SystemExit('frozen bulk tag assignment anchor changed')
path.write_text(text.replace(anchor, replacement, 1))
PY

ruff check --no-cache netbox/extras/managers.py
