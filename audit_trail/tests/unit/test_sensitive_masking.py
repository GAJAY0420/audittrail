"""Validate masking and request metadata behavior within audit signals."""

from __future__ import annotations

from typing import Any

import pytest
from django.contrib.auth import get_user_model

from audit_trail.middleware import set_current_user, set_request_meta
from audit_trail.models import AuditDemoRecord
from audit_trail.storage.outbox.models import AuditEventOutbox
from audit_trail.utils.sensitive import unmask_change


def _set_middleware_state(user: Any, ip: str) -> None:
    set_current_user(user)
    set_request_meta({"ip": ip, "user": getattr(user, "username", str(user))})


def _clear_middleware_state() -> None:
    set_current_user(None)
    set_request_meta(None)


@pytest.mark.django_db
def test_sensitive_field_masked_on_create():
    user_model = get_user_model()
    user = user_model.objects.create_user(username="auditor", password="demo-pass")

    try:
        _set_middleware_state(user, "203.0.113.10")
        AuditDemoRecord.objects.create_demo_record(
            number=100,
            message="Initial record",
            payload={"source": "unit"},
            identity_number="123-45-6789",
        )
    finally:
        _clear_middleware_state()

    entry = AuditEventOutbox.objects.order_by("-created_at").first()
    assert entry is not None
    identity_diff = entry.payload["diff"]["identity_number"]
    assert identity_diff["after"].startswith("masked:")
    assert "encrypted_after" in identity_diff
    assert unmask_change(identity_diff) == "123-45-6789"
    assert entry.context["actor"]["username"] == "auditor"
    assert entry.context["request"]["ip"] == "203.0.113.10"
    assert entry.context["request"]["user"] == "auditor"


@pytest.mark.django_db
def test_sensitive_field_masked_on_update():
    user_model = get_user_model()
    user = user_model.objects.create_user(username="auditor", password="demo-pass")

    try:
        _set_middleware_state(user, "203.0.113.10")
        record = AuditDemoRecord.objects.create_demo_record(
            number=101,
            message="Original",
            payload={"source": "unit"},
            identity_number="111-22-3333",
        )
    finally:
        _clear_middleware_state()

    try:
        _set_middleware_state(user, "198.51.100.5")
        record.identity_number = "999-88-7777"
        record.save()
    finally:
        _clear_middleware_state()

    entry = AuditEventOutbox.objects.order_by("-created_at").first()
    assert entry is not None
    identity_diff = entry.payload["diff"]["identity_number"]
    assert identity_diff["before"].startswith("masked:")
    assert identity_diff["after"].startswith("masked:")
    assert identity_diff["encrypted_before"] != identity_diff["encrypted_after"]
    assert unmask_change(identity_diff, position="before") == "111-22-3333"
    assert unmask_change(identity_diff, position="after") == "999-88-7777"
    assert entry.context["request"]["ip"] == "198.51.100.5"
