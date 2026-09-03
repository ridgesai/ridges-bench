# Restore scalable tag assignment

Assigning an existing set of tags to a NetBox object has become expensive. The
API stays correct for a handful of tags, but the database work now grows with
the number of tags being added instead of staying bounded.

Work in `/app`. Find the manager method that assigns tags to an object and
change only that method. Keep its signature and the rest of its file unchanged,
including imports; use only names the file already imports.

Restore a lazy, database-backed assignment path with these properties:

- adding many existing Tag model instances uses a bounded number of SQL
  statements, independent of how many of them are new;
- tags already attached to the object are not inserted or signaled again;
- duplicate arguments do not create duplicate through rows;
- empty and entirely pre-existing additions are no-ops;
- the method's existing keyword arguments, router-selected database aliases,
  and the existing pre-add and post-add signal contract remain intact; and
- API creation and update continue to expose the exact assigned tag set.

Do not change models, fields, constraints, indexes, migrations, serializers,
signals, tests, fixtures, or unrelated manager methods. Do not materialize
database state outside the existing manager flow. Do not add raw SQL, process,
filesystem, network, repository, or dynamic-code side effects.

Run these checks before finishing:

```bash
python netbox/manage.py test \
  extras.tests.test_tags.TaggedItemTest.test_create_tagged_item \
  extras.tests.test_tags.TaggedItemTest.test_update_tagged_item \
  --keepdb --noinput
```

Also run `ruff check --no-cache` on the file you changed.
