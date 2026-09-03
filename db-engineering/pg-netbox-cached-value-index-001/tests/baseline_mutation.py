#!/usr/bin/env python3
from pathlib import Path

path = Path("/app/netbox/extras/migrations/0107_cachedvalue_extras_cachedvalue_object.py")
anchors = {
    "fields=['object_type', 'object_id']": "fields=['object_type']",
}
text = path.read_text()
for anchor, replacement in anchors.items():
    if text.count(anchor) != 1:
        raise SystemExit("frozen cached-value index anchor changed")
    text = text.replace(anchor, replacement, 1)
path.write_text(text)
