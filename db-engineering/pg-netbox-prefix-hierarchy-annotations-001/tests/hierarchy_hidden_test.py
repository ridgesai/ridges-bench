from ipam.models import Prefix, VRF
from utilities.testing import TestCase


class PrefixHierarchyAnnotationTest(TestCase):
    def annotated(self, prefix):
        return Prefix.objects.filter(pk=prefix.pk).annotate_hierarchy().get()

    def test_duplicate_parent_cidrs_and_child_rows_have_distinct_rules(self):
        root, duplicate_a, duplicate_b, leaf = Prefix.objects.bulk_create(
            [
                Prefix(prefix="10.40.0.0/16"),
                Prefix(prefix="10.40.0.0/20"),
                Prefix(prefix="10.40.0.0/20"),
                Prefix(prefix="10.40.0.0/24"),
            ]
        )

        self.assertEqual(self.annotated(root).hierarchy_depth, 0)
        self.assertEqual(self.annotated(root).hierarchy_children, 3)
        self.assertEqual(self.annotated(duplicate_a).hierarchy_depth, 1)
        self.assertEqual(self.annotated(duplicate_b).hierarchy_children, 1)
        self.assertEqual(self.annotated(leaf).hierarchy_depth, 2)
        self.assertEqual(self.annotated(leaf).hierarchy_children, 0)

    def test_null_and_explicit_vrf_trees_are_isolated(self):
        vrf = VRF.objects.create(name="Isolated tree")
        null_root, null_leaf, vrf_root, vrf_leaf = Prefix.objects.bulk_create(
            [
                Prefix(prefix="10.41.0.0/16", vrf=None),
                Prefix(prefix="10.41.0.0/24", vrf=None),
                Prefix(prefix="10.41.0.0/16", vrf=vrf),
                Prefix(prefix="10.41.0.0/24", vrf=vrf),
            ]
        )

        for root in (null_root, vrf_root):
            self.assertEqual(self.annotated(root).hierarchy_depth, 0)
            self.assertEqual(self.annotated(root).hierarchy_children, 1)
        for leaf in (null_leaf, vrf_leaf):
            self.assertEqual(self.annotated(leaf).hierarchy_depth, 1)
            self.assertEqual(self.annotated(leaf).hierarchy_children, 0)

    def test_ipv6_create_persists_depth_and_children(self):
        root = Prefix.objects.create(prefix="2001:db8:41::/48")
        middle = Prefix.objects.create(prefix="2001:db8:41::/56")
        leaf = Prefix.objects.create(prefix="2001:db8:41::/64")

        root.refresh_from_db()
        middle.refresh_from_db()
        leaf.refresh_from_db()
        self.assertEqual((root._depth, root._children), (0, 2))
        self.assertEqual((middle._depth, middle._children), (1, 1))
        self.assertEqual((leaf._depth, leaf._children), (2, 0))

    def test_move_between_vrfs_recalculates_both_trees(self):
        vrf_a = VRF.objects.create(name="Move A")
        vrf_b = VRF.objects.create(name="Move B")
        root_a = Prefix.objects.create(prefix="10.42.0.0/16", vrf=vrf_a)
        root_b = Prefix.objects.create(prefix="10.42.0.0/16", vrf=vrf_b)
        child = Prefix.objects.create(prefix="10.42.0.0/24", vrf=vrf_a)

        child.vrf = vrf_b
        child.save()
        root_a.refresh_from_db()
        root_b.refresh_from_db()
        child.refresh_from_db()

        self.assertEqual((root_a._depth, root_a._children), (0, 0))
        self.assertEqual((root_b._depth, root_b._children), (0, 1))
        self.assertEqual((child._depth, child._children), (1, 0))

    def test_delete_recalculates_surviving_tree(self):
        root = Prefix.objects.create(prefix="10.43.0.0/16")
        middle = Prefix.objects.create(prefix="10.43.0.0/20")
        leaf = Prefix.objects.create(prefix="10.43.0.0/24")

        middle.delete()
        root.refresh_from_db()
        leaf.refresh_from_db()

        self.assertEqual((root._depth, root._children), (0, 1))
        self.assertEqual((leaf._depth, leaf._children), (1, 0))
