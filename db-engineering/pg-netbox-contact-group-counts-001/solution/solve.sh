#!/bin/bash
set -euo pipefail

cd /app
python - <<'PY'
from pathlib import Path

path = Path('netbox/tenancy/models/contacts.py')
text = path.read_text()
anchor = """    def annotate_contacts(self):
        \"\"\"
        Annotate the total number of Contacts belonging to each ContactGroup.

        This returns both direct children and children of child groups. Raw SQL is used here to avoid double-counting
        contacts which are assigned to multiple child groups of the parent.
        \"\"\"
        return self.annotate(
            contact_count=RawSQL(
                \"SELECT COUNT(DISTINCT m2m.contact_id)\"
                \" FROM tenancy_contact_groups m2m\"
                \" INNER JOIN tenancy_contactgroup cg ON m2m.contactgroup_id = cg.id\"
                \" WHERE cg.tree_id = tenancy_contactgroup.tree_id\"
                \" AND (cg.id = tenancy_contactgroup.id\"
                \" OR cg.parent_id = tenancy_contactgroup.id)\",
                ()
            )
        )
"""
replacement = """    def annotate_contacts(self):
        \"\"\"
        Annotate the total number of Contacts belonging to each ContactGroup.

        This returns both direct children and children of child groups. Raw SQL is used here to avoid double-counting
        contacts which are assigned to multiple child groups of the parent.
        \"\"\"
        return self.annotate(
            contact_count=RawSQL(
                \"SELECT COUNT(DISTINCT m2m.contact_id)\"
                \" FROM tenancy_contact_groups m2m\"
                \" INNER JOIN tenancy_contactgroup cg ON m2m.contactgroup_id = cg.id\"
                \" WHERE cg.tree_id = tenancy_contactgroup.tree_id\"
                \" AND cg.lft >= tenancy_contactgroup.lft\"
                \" AND cg.lft <= tenancy_contactgroup.rght\",
                ()
            )
        )
"""
if text.count(anchor) != 1:
    raise SystemExit('frozen contact-group annotation anchor changed')
path.write_text(text.replace(anchor, replacement, 1))
PY

ruff check --no-cache netbox/tenancy/models/contacts.py
