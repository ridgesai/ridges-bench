# Author prefix hierarchy annotations

NetBox updates each Prefix's persisted depth and descendant count after prefix
creation, movement, and deletion. The queryset method supplying those two
annotations currently returns placeholder zeroes, so the hierarchy fields no
longer track the real prefix tree.

Work in `/app`. Limit production changes to `netbox/ipam/querysets.py`,
specifically `PrefixQuerySet.annotate_hierarchy()`. Keep the method signature
and the rest of the file unchanged, including imports; use only names the file
already imports.

The method must return the same queryset annotated with:

- `hierarchy_depth`: the number of distinct strict parent CIDRs containing the
  row's prefix in the same VRF;
- `hierarchy_children`: the number of strict descendant rows contained by the
  row's prefix in the same VRF.

Two NULL VRFs belong to the same routing table. A NULL VRF and an explicit VRF,
or two different explicit VRFs, must remain isolated. A prefix must not count
itself. Duplicate parent CIDRs count once toward depth, while duplicate child
rows count individually toward the descendant total. Preserve IPv4 and IPv6
behavior and keep evaluation lazy and database-backed. Write the method as
plain ORM expressions: no Python loops, comprehensions, lambdas, exception
handling, or context managers inside it.

The existing save and delete signals must continue to persist correct `_depth`
and `_children` values after create, move, and delete operations. Do not change
models, fields, indexes, migrations, signals, serializers, tests, fixtures, or
unrelated methods. Do not add database writes, process, filesystem, network,
repository, or dynamic-code side effects to the queryset method.

Run `python netbox/manage.py test ipam.tests.test_models.TestPrefixHierarchy
--keepdb --noinput` and `ruff check --no-cache netbox/ipam/querysets.py` before
finishing.
