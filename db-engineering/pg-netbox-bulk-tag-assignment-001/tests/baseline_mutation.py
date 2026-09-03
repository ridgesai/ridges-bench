#!/usr/bin/env python3
from pathlib import Path

path = Path("/app/netbox/extras/managers.py")
anchor = '''        # Use a single bulk INSERT instead of one get_or_create per tag.
        self.through._default_manager.using(db).bulk_create(
            [
                self.through(tag=tag, **lookup, **(through_defaults or {}))
                for tag in tag_objs
                if tag.pk in new_ids
            ],
            ignore_conflicts=True,
        )
'''
replacement = '''        # Insert each relationship independently.
        for tag in tag_objs:
            if tag.pk in new_ids:
                self.through._default_manager.using(db).get_or_create(
                    tag=tag,
                    defaults=through_defaults or {},
                    **lookup,
                )
'''
text = path.read_text()
if text.count(anchor) != 1:
    raise SystemExit("frozen bulk tag assignment anchor changed")
path.write_text(text.replace(anchor, replacement, 1))
