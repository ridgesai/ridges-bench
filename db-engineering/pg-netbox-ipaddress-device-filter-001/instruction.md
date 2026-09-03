# Optimize the IP-address device filter

NetBox's IP-address device filter currently resolves matching devices, checks
whether any exist, then issues another interface query for every selected
device before it can filter IP addresses. Query work therefore grows with the
number of selected devices.

Work in `/app`. Limit production changes to `netbox/ipam/filtersets.py`,
specifically `IPAddressFilterSet.filter_device()`. Keep its signature and the
rest of the file unchanged, including imports; use only names the file already
imports.

Return the same lazy queryset while performing a bounded number of SQL queries
independent of how many device names or IDs are selected:

- IP addresses directly assigned to every selected device must match;
- selecting a virtual-chassis master also includes non-management interfaces
  on every member of that chassis;
- selecting a non-master member does not expand to its master or peers;
- a selected device's own management interface remains eligible, but a master
  does not inherit management-only interfaces from peers;
- multiple values use any-of semantics;
- empty and unmatched selections return no rows;
- existing queryset filters, ordering, name filters, and ID filters compose.

Keep all selection and filtering database-backed. Do not materialize devices,
interfaces, or IP addresses in Python. Write the method as plain ORM
expressions: no Python loops, comprehensions, lambdas, exception handling, or
context managers inside it. Do not change `Device.vc_interfaces()`, models,
fields, indexes, migrations, views, serializers, tests, fixtures, or unrelated
filter methods. Do not add database writes, process, filesystem, network,
repository, or dynamic-code side effects.

Run these checks before finishing:

```bash
python netbox/manage.py test \
  ipam.tests.test_filtersets.IPAddressTestCase.test_device \
  --keepdb --noinput
ruff check --no-cache netbox/ipam/filtersets.py
```
