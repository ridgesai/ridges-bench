import json

from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase

from dcim.models import Site
from extras.models import CachedValue
from netbox.search.backends import search_backend


INDEX_NAME = "extras_cachedvalue_object"
MIGRATION = "0107_cachedvalue_extras_cachedvalue_object"
NOISE_ROWS = 120_000
TARGET_ROWS = 7


def plan_nodes(plan):
    yield plan
    for child in plan.get("Plans", []):
        yield from plan_nodes(child)


class CachedValueIndexHiddenTest(TestCase):
    def test_migration_state_matches_composite_model_index(self):
        state = MigrationExecutor(connection).loader.project_state([("extras", MIGRATION)])
        model = state.apps.get_model("extras", "CachedValue")
        indexes = {index.name: list(index.fields) for index in model._meta.indexes}
        self.assertEqual(indexes.get(INDEX_NAME), ["object_type", "object_id"])

    def test_exact_object_delete_is_correct_and_selective(self):
        site = Site.objects.create(name="Index target", slug="index-target")
        object_type = ContentType.objects.get_for_model(Site)
        CachedValue.objects.all().delete()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO extras_cachedvalue
                    (id, timestamp, object_type_id, object_id, field, type, value, weight)
                SELECT gen_random_uuid(), NOW(), %s, 1000000 + value,
                       'name', 'string', 'noise-' || value::text, 1000
                FROM generate_series(1, %s) AS value
                """,
                [object_type.pk, NOISE_ROWS],
            )
            cursor.execute(
                """
                INSERT INTO extras_cachedvalue
                    (id, timestamp, object_type_id, object_id, field, type, value, weight)
                SELECT gen_random_uuid(), NOW(), %s, %s,
                       'target-' || value::text, 'string', 'target', 1000
                FROM generate_series(1, %s) AS value
                """,
                [object_type.pk, site.pk, TARGET_ROWS],
            )
            cursor.execute("ANALYZE extras_cachedvalue")
            cursor.execute(
                "SELECT indexdef FROM pg_indexes "
                "WHERE schemaname='public' AND tablename='extras_cachedvalue' "
                "AND indexname=%s",
                [INDEX_NAME],
            )
            index_rows = cursor.fetchall()

        self.assertEqual(len(index_rows), 1)
        normalized_index = " ".join(index_rows[0][0].split())
        self.assertIn("(object_type_id, object_id)", normalized_index)

        queryset = CachedValue.objects.filter(
            object_type=object_type,
            object_id=site.pk,
        )
        plan_document = json.loads(
            queryset.explain(format="json", analyze=True, buffers=True, verbose=True)
        )
        plan = plan_document[0]["Plan"]
        nodes = list(plan_nodes(plan))
        index_names = sorted(
            {node["Index Name"] for node in nodes if node.get("Index Name")}
        )
        root_buffers = sum(
            int(plan.get(field, 0))
            for field in (
                "Shared Hit Blocks",
                "Shared Read Blocks",
                "Shared Dirtied Blocks",
                "Shared Written Blocks",
            )
        )
        self.assertIn(INDEX_NAME, index_names)
        self.assertEqual(int(plan["Actual Rows"]), TARGET_ROWS)
        self.assertLess(root_buffers, 100)

        captured_deletes = []

        def capture_delete(execute, sql, params, many, context):
            if sql.lstrip().upper().startswith("DELETE FROM"):
                captured_deletes.append((sql, tuple(params or ())))
            return execute(sql, params, many, context)

        with connection.execute_wrapper(capture_delete):
            deleted = search_backend.remove(site)

        self.assertEqual(deleted, TARGET_ROWS)
        self.assertEqual(len(captured_deletes), 1)
        delete_sql = " ".join(captured_deletes[0][0].split()).lower()
        self.assertIn("object_type_id", delete_sql)
        self.assertIn("object_id", delete_sql)
        self.assertFalse(queryset.exists())
        self.assertEqual(CachedValue.objects.count(), NOISE_ROWS)

        print(
            "RIDGES_INDEX_EVIDENCE="
            + json.dumps(
                {
                    "deleted": deleted,
                    "index_names": index_names,
                    "noise_rows": NOISE_ROWS,
                    "root_buffers": root_buffers,
                    "target_rows": TARGET_ROWS,
                },
                sort_keys=True,
            )
        )
