from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status

from ipam.models import VLAN, VLANGroup
from utilities.data import string_to_ranges
from utilities.testing import APITestCase, TestCase


def create_group(name, slug, ranges, vlan_ids):
    group = VLANGroup.objects.create(
        name=name,
        slug=slug,
        vid_ranges=string_to_ranges(ranges),
    )
    VLAN.objects.bulk_create(
        VLAN(group=group, vid=vid, name=f"{name} VLAN {vid}") for vid in vlan_ids
    )
    return group


class VLANGroupUtilizationHiddenModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.fractional = create_group(
            "Ridges VLAN fractional",
            "ridges-vlan-fractional",
            "100-105",
            [100],
        )
        cls.decimal = create_group(
            "Ridges VLAN decimal",
            "ridges-vlan-decimal",
            "200-207",
            [200, 201, 202],
        )
        cls.whole = create_group(
            "Ridges VLAN whole",
            "ridges-vlan-whole",
            "300-303",
            [300, 301],
        )
        cls.empty = create_group(
            "Ridges VLAN empty",
            "ridges-vlan-empty",
            "400-402",
            [],
        )
        cls.disjoint = create_group(
            "Ridges VLAN disjoint",
            "ridges-vlan-disjoint",
            "500-502,600-601",
            [500, 600],
        )

    def annotated(self):
        return {
            row["slug"]: row
            for row in VLANGroup.objects.annotate_utilization().values(
                "slug", "vlan_count", "total_vlan_ids", "utilization"
            )
        }

    def test_fractional_and_whole_utilization(self):
        rows = self.annotated()
        self.assertEqual(rows[self.fractional.slug]["vlan_count"], 1)
        self.assertEqual(rows[self.fractional.slug]["total_vlan_ids"], 6)
        self.assertAlmostEqual(rows[self.fractional.slug]["utilization"], 16.67, places=2)
        self.assertAlmostEqual(rows[self.decimal.slug]["utilization"], 37.5, places=2)
        self.assertAlmostEqual(rows[self.whole.slug]["utilization"], 50.0, places=2)

    def test_empty_and_custom_range_groups(self):
        rows = self.annotated()
        self.assertEqual(rows[self.empty.slug]["vlan_count"], 0)
        self.assertEqual(rows[self.empty.slug]["utilization"], 0.0)
        self.assertEqual(rows[self.disjoint.slug]["total_vlan_ids"], 5)
        self.assertAlmostEqual(rows[self.disjoint.slug]["utilization"], 40.0, places=2)

    def test_filtered_ordered_values_query_is_single_statement(self):
        queryset = (
            VLANGroup.objects.filter(
                pk__in=(self.fractional.pk, self.decimal.pk, self.whole.pk)
            )
            .annotate_utilization()
            .order_by("slug")
            .values_list("slug", "utilization")
        )
        with CaptureQueriesContext(connection) as captured:
            rows = dict(queryset)

        self.assertEqual(len(captured), 1)
        self.assertAlmostEqual(rows[self.fractional.slug], 16.67, places=2)
        self.assertAlmostEqual(rows[self.decimal.slug], 37.5, places=2)
        self.assertAlmostEqual(rows[self.whole.slug], 50.0, places=2)


class VLANGroupUtilizationHiddenAPITest(APITestCase):
    def test_list_api_exposes_the_same_rounded_utilization(self):
        group = create_group(
            "Ridges VLAN API fractional",
            "ridges-vlan-api-fractional",
            "700-705",
            [700],
        )
        self.add_permissions("ipam.view_vlangroup")

        response = self.client.get(
            f"{reverse('ipam-api:vlangroup-list')}?id={group.pk}",
            **self.header,
        )

        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["vlan_count"], 1)
        self.assertEqual(float(response.data["results"][0]["utilization"]), 16.67)
