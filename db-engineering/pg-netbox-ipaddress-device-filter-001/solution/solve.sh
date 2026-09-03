#!/bin/bash
set -euo pipefail

cd /app
python - <<'PY'
from pathlib import Path

path = Path('netbox/ipam/filtersets.py')
text = path.read_text()
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
replacement = """    def filter_device(self, queryset, name, value):
        devices = Device.objects.filter(**{'{}__in'.format(name): value})
        return queryset.filter(
            Q(interface__device__in=devices) |
            Q(
                interface__device__virtual_chassis__master__in=devices,
                interface__mgmt_only=False
            )
        )
"""
if text.count(anchor) != 1:
    raise SystemExit('frozen IP-address device-filter anchor changed')
path.write_text(text.replace(anchor, replacement, 1))
PY

ruff check --no-cache netbox/ipam/filtersets.py
