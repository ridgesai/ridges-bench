#!/usr/bin/env python3
from pathlib import Path

path = Path("/app/netbox/ipam/filtersets.py")
anchor = """    def filter_device(self, queryset, name, value):
        devices = Device.objects.filter(**{'{}__in'.format(name): value})
        if not devices.exists():
            return queryset.none()
        interface_ids = []
        for device in devices:
            interface_ids.extend(device.vc_interfaces().values_list('id', flat=True))
        return queryset.filter(
            interface__in=interface_ids
        )
"""
text = path.read_text()
if text.count(anchor) != 1:
    raise SystemExit("frozen IP-address device-filter anchor changed")
