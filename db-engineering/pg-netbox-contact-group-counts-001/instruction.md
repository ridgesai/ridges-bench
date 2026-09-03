# Repair descendant contact counts

NetBox annotates every contact group with `contact_count` for the list and REST
API. The current query counts contacts assigned directly to a group or to one
of its immediate children, but silently omits contacts assigned farther down
the hierarchy.

Work in `/app`. Limit production changes to
`netbox/tenancy/models/contacts.py`, specifically
`ContactGroupManager.annotate_contacts()`. Keep its signature and the rest of
the file unchanged, including imports; use only names the file already imports.

Return a lazy, composable queryset whose `contact_count` is the number of
distinct contacts assigned to the group itself or to any descendant at any
depth:

- contacts assigned at multiple descendant levels count once;
- unrelated trees never contribute, even when their MPTT bounds overlap;
- empty groups return integer zero;
- filtered, ordered, sliced, and values-based querysets retain the annotation;
- list/API serialization receives the same exact counts;
- evaluating any number of annotated groups uses one database query.

Keep the aggregation database-backed. Do not materialize groups or contacts in
Python. Write the method as plain ORM expressions: no Python loops,
comprehensions, lambdas, exception handling, or context managers inside it. Do
not change models, fields, indexes, migrations, views, serializers, tests,
fixtures, manager registration, or unrelated methods. Do not add database
writes, process, filesystem, network, repository, or dynamic-code side effects.

Run these checks before finishing:

```bash
python netbox/manage.py test \
  tenancy.tests.test_models.ContactGroupTestCase \
  --keepdb --noinput
ruff check --no-cache netbox/tenancy/models/contacts.py
```
