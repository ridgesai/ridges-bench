# Repair VLAN-group utilization

NetBox annotates VLAN groups with both their VLAN count and percentage
utilization. The current expression performs integer division, so every
non-whole percentage is truncated before `Round()` sees it. Common empty and
fully-used groups mask the defect.

Work in `/app`. Limit production changes to `netbox/ipam/querysets.py`,
specifically `VLANGroupQuerySet.annotate_utilization()`. Keep its signature and
the rest of the file unchanged, including imports; use only names the file
already imports.

Return a lazy, composable queryset with these exact annotations:

- `vlan_count` is the database count of VLANs related to the group;
- `utilization` is `vlan_count * 100 / total_vlan_ids`, rounded to two decimal
  places without truncating fractional values first;
- empty groups produce numeric zero;
- default and custom VLAN-ID ranges use their stored `total_vlan_ids` value;
- filtered, ordered, sliced, and values-based querysets retain both annotations;
- list/API serialization exposes the same rounded result; and
- evaluating any number of groups uses one database query.

Keep the count and arithmetic database-backed. Do not materialize groups or
VLANs in Python. Write the method as plain ORM expressions: no Python loops,
comprehensions, lambdas, exception handling, or context managers inside it. Do
not change models, fields, range calculation, indexes, migrations, views,
serializers, tests, fixtures, manager registration, or unrelated methods. Do
not add database writes, process, filesystem, network, repository, or
dynamic-code side effects.

Run these checks before finishing:

```bash
python netbox/manage.py test \
  ipam.tests.test_api.VLANGroupTest.test_list_objects \
  --keepdb --noinput
ruff check --no-cache netbox/ipam/querysets.py
```
