#!/usr/bin/env python3
from pathlib import Path

path = Path("/app/netbox/ipam/querysets.py")
anchor = '''    def annotate_utilization(self):
        from .models import VLAN

        return self.annotate(
            vlan_count=count_related(VLAN, 'group'),
            utilization=Round(F('vlan_count') * 100.0 / F('total_vlan_ids'), 2),
        )
'''
replacement = '''    def annotate_utilization(self):
        from .models import VLAN

        return self.annotate(
            vlan_count=count_related(VLAN, 'group'),
            utilization=Round(F('vlan_count') * 100 / F('total_vlan_ids'), 2),
        )
'''
text = path.read_text()
if text.count(anchor) != 1:
    raise SystemExit("frozen VLAN utilization anchor changed")
path.write_text(text.replace(anchor, replacement, 1))
