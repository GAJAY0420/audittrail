"""Tests covering the demo audit model and its helpers."""

from __future__ import annotations

import pytest
from django.core.management import call_command

from audit_trail.models import AuditDemoRecord


@pytest.mark.django_db
def test_seed_records_creates_expected_objects():
    """seed_records should create the requested number of demo objects."""

    created = AuditDemoRecord.objects.seed_records(
        count=2,
        prefix="Demo",
        base_payload={"source": "unit-test"},
        starting_number=10,
    )
    assert len(created) == 2
    assert AuditDemoRecord.objects.count() == 2
    assert created[0].structured_payload["source"] == "unit-test"
    assert created[0].structured_payload["ordinal"] == 10


@pytest.mark.django_db
def test_management_command_generates_records():
    """Management command should mirror the manager helper behavior."""

    call_command("audittrail_generate_dummy_events", count=3, prefix="Cmd", start=5)
    assert AuditDemoRecord.objects.count() == 3
    sample = AuditDemoRecord.objects.order_by("numeric_value").first()
    assert sample is not None
    assert sample.numeric_value == 5
