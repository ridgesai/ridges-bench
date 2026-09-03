from django.db import connection
from django.test.utils import CaptureQueriesContext

from dcim.models import Device, Interface, VirtualChassis
from ipam.filtersets import IPAddressFilterSet
from ipam.models import IPAddress
from utilities.testing import TestCase, create_test_device


class IPAddressDeviceFilterHiddenTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ordinary = create_test_device("filter-ordinary")
        cls.master = create_test_device("filter-master")
        cls.member = create_test_device("filter-member")
        cls.peer = create_test_device("filter-peer")

        chassis = VirtualChassis.objects.create(
            name="Filter virtual chassis",
            master=cls.master,
        )
        Device.objects.filter(pk=cls.master.pk).update(
            virtual_chassis=chassis,
            vc_position=1,
        )
        Device.objects.filter(pk=cls.member.pk).update(
            virtual_chassis=chassis,
            vc_position=2,
        )
        Device.objects.filter(pk=cls.peer.pk).update(
            virtual_chassis=chassis,
            vc_position=3,
        )
        for device in (cls.master, cls.member, cls.peer):
            device.refresh_from_db()

        cls.ordinary_interface = Interface.objects.create(
            device=cls.ordinary,
            name="ordinary-eth0",
        )
        cls.master_management = Interface.objects.create(
            device=cls.master,
            name="master-mgmt",
            mgmt_only=True,
        )
        cls.member_interface = Interface.objects.create(
            device=cls.member,
            name="member-eth0",
        )
        cls.member_management = Interface.objects.create(
            device=cls.member,
            name="member-mgmt",
            mgmt_only=True,
        )
        cls.peer_interface = Interface.objects.create(
            device=cls.peer,
            name="peer-eth0",
        )

        cls.ordinary_ip = IPAddress.objects.create(
            address="10.81.0.1/24",
            assigned_object=cls.ordinary_interface,
            dns_name="selected-ordinary",
        )
        cls.master_ip = IPAddress.objects.create(
            address="10.81.1.1/24",
            assigned_object=cls.master_management,
            dns_name="selected-master",
        )
        cls.member_ip = IPAddress.objects.create(
            address="10.81.2.1/24",
            assigned_object=cls.member_interface,
            dns_name="selected-member",
        )
        cls.member_management_ip = IPAddress.objects.create(
            address="10.81.3.1/24",
            assigned_object=cls.member_management,
            dns_name="selected-member-management",
        )
        cls.peer_ip = IPAddress.objects.create(
            address="10.81.4.1/24",
            assigned_object=cls.peer_interface,
            dns_name="excluded-peer",
        )

    def filtered(self, name, values, queryset=None):
        base = queryset if queryset is not None else IPAddress.objects.all()
        return IPAddressFilterSet().filter_device(base, name, values).order_by("address", "pk")

    def test_ordinary_device_name_id_and_empty_selection(self):
        self.assertEqual(
            list(self.filtered("name", [self.ordinary.name])),
            [self.ordinary_ip],
        )
        self.assertEqual(
            list(self.filtered("pk", [self.ordinary.pk])),
            [self.ordinary_ip],
        )
        self.assertEqual(list(self.filtered("name", ["missing-device"])), [])
        self.assertEqual(list(self.filtered("pk", [])), [])

    def test_virtual_chassis_master_expands_non_management_peers(self):
        self.assertEqual(
            set(self.filtered("pk", [self.master.pk])),
            {self.master_ip, self.member_ip, self.peer_ip},
        )

    def test_virtual_chassis_member_does_not_expand_to_peers(self):
        self.assertEqual(
            set(self.filtered("pk", [self.member.pk])),
            {self.member_ip, self.member_management_ip},
        )

    def test_multiple_devices_and_existing_queryset_filter_compose(self):
        queryset = IPAddress.objects.filter(dns_name__startswith="selected-")
        self.assertEqual(
            set(self.filtered("name", [self.ordinary.name, self.master.name], queryset)),
            {self.ordinary_ip, self.master_ip, self.member_ip},
        )

    def test_query_count_is_bounded_by_selection_size(self):
        names = []
        expected = []
        for index in range(8):
            device = create_test_device(f"filter-scale-{index}")
            interface = Interface.objects.create(device=device, name="eth0")
            ip = IPAddress.objects.create(
                address=f"10.82.{index}.1/24",
                assigned_object=interface,
            )
            names.append(device.name)
            expected.append(ip.pk)

        with CaptureQueriesContext(connection) as captured:
            actual = list(
                self.filtered("name", names).values_list("pk", flat=True)
            )

        self.assertEqual(sorted(actual), sorted(expected))
        self.assertLessEqual(len(captured), 3)
