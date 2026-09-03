from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status

from tenancy.models import Contact, ContactGroup
from utilities.testing import APITestCase, TestCase


class ContactGroupCountsHiddenModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = ContactGroup.objects.create(name="Ridges deep root", slug="ridges-deep-root")
        cls.branch = ContactGroup.objects.create(
            name="Ridges deep branch",
            slug="ridges-deep-branch",
            parent=cls.root,
        )
        cls.leaf = ContactGroup.objects.create(
            name="Ridges deep leaf",
            slug="ridges-deep-leaf",
            parent=cls.branch,
        )
        cls.great_leaf = ContactGroup.objects.create(
            name="Ridges deep great leaf",
            slug="ridges-deep-great-leaf",
            parent=cls.leaf,
        )
        cls.sibling = ContactGroup.objects.create(
            name="Ridges deep sibling",
            slug="ridges-deep-sibling",
            parent=cls.root,
        )
        cls.other_root = ContactGroup.objects.create(
            name="Ridges other root",
            slug="ridges-other-root",
        )
        cls.empty_root = ContactGroup.objects.create(
            name="Ridges empty root",
            slug="ridges-empty-root",
        )

        root_contact = Contact.objects.create(name="Ridges root contact")
        branch_contact = Contact.objects.create(name="Ridges branch contact")
        leaf_contact = Contact.objects.create(name="Ridges leaf contact")
        great_contact = Contact.objects.create(name="Ridges great contact")
        overlap_contact = Contact.objects.create(name="Ridges overlap contact")
        sibling_contact = Contact.objects.create(name="Ridges sibling contact")
        other_contact = Contact.objects.create(name="Ridges other contact")

        root_contact.groups.add(cls.root)
        branch_contact.groups.add(cls.branch)
        leaf_contact.groups.add(cls.leaf)
        great_contact.groups.add(cls.great_leaf)
        overlap_contact.groups.add(cls.branch, cls.great_leaf)
        sibling_contact.groups.add(cls.sibling)
        other_contact.groups.add(cls.other_root)

    def annotated_counts(self):
        return dict(
            ContactGroup.objects.annotate_contacts().values_list("slug", "contact_count")
        )

    def test_arbitrary_depth_and_cross_level_distinctness(self):
        counts = self.annotated_counts()
        self.assertEqual(counts[self.root.slug], 6)
        self.assertEqual(counts[self.branch.slug], 4)
        self.assertEqual(counts[self.leaf.slug], 3)
        self.assertEqual(counts[self.great_leaf.slug], 2)
        self.assertEqual(counts[self.sibling.slug], 1)

    def test_other_trees_and_empty_groups_are_isolated(self):
        counts = self.annotated_counts()
        self.assertEqual(counts[self.other_root.slug], 1)
        self.assertEqual(counts[self.empty_root.slug], 0)
        self.assertEqual(counts[self.root.slug], 6)

    def test_filtered_ordered_values_query_is_single_statement(self):
        queryset = (
            ContactGroup.objects.annotate_contacts()
            .filter(tree_id=self.root.tree_id, name__startswith="Ridges deep")
            .order_by("name")
            .values_list("slug", "contact_count")
        )
        with CaptureQueriesContext(connection) as captured:
            rows = list(queryset)

        self.assertEqual(len(captured), 1)
        self.assertEqual(dict(rows)[self.root.slug], 6)
        self.assertEqual(dict(rows)[self.great_leaf.slug], 2)


class ContactGroupCountsHiddenAPITest(APITestCase):
    def test_detail_api_exposes_deep_descendant_count(self):
        root = ContactGroup.objects.create(name="API root", slug="api-count-root")
        child = ContactGroup.objects.create(
            name="API child",
            slug="api-count-child",
            parent=root,
        )
        grandchild = ContactGroup.objects.create(
            name="API grandchild",
            slug="api-count-grandchild",
            parent=child,
        )
        contact = Contact.objects.create(name="API deep contact")
        contact.groups.add(grandchild)
        self.add_permissions("tenancy.view_contactgroup")

        response = self.client.get(
            reverse("tenancy-api:contactgroup-detail", kwargs={"pk": root.pk}),
            **self.header,
        )

        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.data["contact_count"], 1)
