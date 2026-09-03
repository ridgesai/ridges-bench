#!/usr/bin/env python3
from pathlib import Path

path = Path("/app/netbox/ipam/querysets.py")
original = """        return self.annotate(
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
placeholder = """        return self.annotate(
            hierarchy_depth=RawSQL('0', ()),
            hierarchy_children=RawSQL('0', ()),
        )
"""
text = path.read_text()
if text.count(original) != 1:
    raise SystemExit("frozen prefix hierarchy annotation anchor changed")
path.write_text(text.replace(original, placeholder, 1))
