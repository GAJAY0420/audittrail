from __future__ import annotations

from django.test import TestCase

from audit_trail.storage.outbox.models import AuditEventOutbox
from audit_trail.tests.testapp.models import (
    Address,
    BusinessPartner,
    BusinessPartnerRole,
)


class M2MAuditingTests(TestCase):
    databases = {"default"}

    def setUp(self) -> None:  # noqa: D401
        super().setUp()
        AuditEventOutbox.objects.all().delete()

    def tearDown(self) -> None:  # noqa: D401
        AuditEventOutbox.objects.all().delete()
        super().tearDown()

    def test_roles_addition_creates_audit_event(self) -> None:
        partner = BusinessPartner.objects.create(first_name="Ada")
        role = BusinessPartnerRole.objects.create(name="Manager")
        AuditEventOutbox.objects.all().delete()

        partner.roles.add(role)

        entry = AuditEventOutbox.objects.latest("created_at")
        diff = entry.payload["diff"].get("roles")
        self.assertIsNotNone(diff)
        assert diff is not None  # for type checkers
        self.assertEqual(entry.payload["event_type"], "updated")
        self.assertEqual(len(diff["added"]), 1)
        self.assertEqual(diff["added"][0]["pk"], role.pk)
        self.assertEqual(diff["relation"], "many_to_many")

    def test_addresses_addition_via_through_model_is_recorded(self) -> None:
        partner = BusinessPartner.objects.create(first_name="Ivan")
        address = Address.objects.create(label="HQ")
        AuditEventOutbox.objects.all().delete()

        partner.addresses.add(address, through_defaults={"nickname": "HQ"})

        entry = AuditEventOutbox.objects.latest("created_at")
        diff = entry.payload["diff"].get("addresses")
        self.assertIsNotNone(diff)
        assert diff is not None
        self.assertTrue(str(diff.get("model", "")).endswith("Address"))
        self.assertEqual(len(diff["added"]), 1)
        self.assertEqual(diff["added"][0]["pk"], address.pk)
