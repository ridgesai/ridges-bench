from django.db import connection
from django.db.models import signals
from django.test.utils import CaptureQueriesContext

from dcim.models import Site
from extras.models import Tag
from utilities.testing import TestCase


def make_tags(prefix, count):
    return Tag.objects.bulk_create(
        [
            Tag(name=f"{prefix} {index:02d}", slug=f"{prefix.lower()}-{index:02d}")
            for index in range(count)
        ]
    )


class BulkTagAssignmentHiddenTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.site = Site.objects.create(name="Ridges tag site", slug="ridges-tag-site")
        cls.tags = make_tags("Ridges bulk tag", 48)

    def capture_add(self, *tags):
        with CaptureQueriesContext(connection) as captured:
            self.site.tags.add(*tags)
        return len(captured)

    def test_many_new_tags_use_bounded_queries(self):
        query_count = self.capture_add(*self.tags)

        self.assertSetEqual(
            set(self.site.tags.values_list("pk", flat=True)),
            {tag.pk for tag in self.tags},
        )
        self.assertLessEqual(query_count, 6)

    def test_query_count_does_not_scale_with_new_tag_count(self):
        small_site = Site.objects.create(name="Small tag site", slug="small-tag-site")
        large_site = Site.objects.create(name="Large tag site", slug="large-tag-site")

        with CaptureQueriesContext(connection) as small:
            small_site.tags.add(*self.tags[:2])
        with CaptureQueriesContext(connection) as large:
            large_site.tags.add(*self.tags[2:42])

        self.assertLessEqual(len(large), len(small) + 1)
        self.assertEqual(large_site.tags.count(), 40)

    def test_existing_and_duplicate_tags_are_not_resignaled(self):
        self.site.tags.add(*self.tags[:3])
        events = []

        def receiver(sender, action, pk_set, **kwargs):
            if action in {"pre_add", "post_add"}:
                events.append((action, set(pk_set)))

        through = self.site.tags.through
        signals.m2m_changed.connect(receiver, sender=through)
        try:
            self.site.tags.add(
                self.tags[0],
                self.tags[1],
                self.tags[3],
                self.tags[3],
                self.tags[4],
            )
        finally:
            signals.m2m_changed.disconnect(receiver, sender=through)

        expected = {self.tags[3].pk, self.tags[4].pk}
        self.assertEqual(events, [("pre_add", expected), ("post_add", expected)])
        self.assertEqual(self.site.tags.count(), 5)

    def test_entirely_existing_addition_is_a_query_bounded_noop(self):
        self.site.tags.add(*self.tags[:12])
        before = set(self.site.tags.values_list("pk", flat=True))

        query_count = self.capture_add(*self.tags[:12])

        self.assertSetEqual(set(self.site.tags.values_list("pk", flat=True)), before)
        self.assertLessEqual(query_count, 2)
