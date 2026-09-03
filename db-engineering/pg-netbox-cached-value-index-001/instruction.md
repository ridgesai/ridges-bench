# Restore the cached-object maintenance index

NetBox removes and refreshes search-cache rows for one exact object by filtering
on both its content type and object ID. The migration that creates the named
maintenance index currently covers only the broad content-type prefix. Search
results remain correct, but an exact object refresh or delete can scan every
cached value for that model.

Repair the production migration so the existing named index selectively serves
the exact-object predicate used by `CachedValueSearchBackend`. Preserve the
migration dependency, model, index name, and all unrelated source.

You may edit only
`netbox/extras/migrations/0107_cachedvalue_extras_cachedvalue_object.py`.
Keep it as a normal bounded Django schema migration. Do not change the cached
value model, search backend, query code, tests, settings, or runtime state. Do
not add file, process, network, or fixture-specific behavior.

The migration must apply cleanly to a fresh schema and leave the migration
state consistent with the model. When many cached objects share one content
type, PostgreSQL must use the named index for the production exact-object
removal and refresh predicate, with bounded buffer work; the exact deleted and
surviving rows and the named index columns are part of the contract. A
content-type-only index is not sufficient.

Run the focused checks with:

```bash
python netbox/manage.py test netbox.tests.test_search.SearchBackendTestCase \
  --keepdb --noinput --verbosity 2
ruff check --no-cache \
  netbox/extras/migrations/0107_cachedvalue_extras_cachedvalue_object.py
```
