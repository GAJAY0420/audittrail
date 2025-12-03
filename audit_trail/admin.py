"""Admin registration for audit trail models."""

from __future__ import annotations

from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.http import HttpRequest

from audit_trail.models import AuditDemoRecord
from audit_trail.storage.outbox.models import AuditEventOutbox


_ORIGINAL_HAS_PERMISSION = AdminSite.has_permission


def _superuser_has_permission(self: AdminSite, request: HttpRequest) -> bool:
    if (
        bool(getattr(request, "user", None))
        and request.user.is_active
        and request.user.is_superuser
    ):
        return True
    return _ORIGINAL_HAS_PERMISSION(self, request)


AdminSite.has_permission = _superuser_has_permission  # type: ignore[assignment]


@admin.register(AuditEventOutbox)
class AuditEventOutboxAdmin(admin.ModelAdmin):
    """Expose audit outbox records in Django admin for inspection/debugging."""

    list_display = (
        "id",
        "model_label",
        "object_pk",
        "status",
        "attempts",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "model_label", "created_at")
    search_fields = ("model_label", "object_pk", "last_error")
    readonly_fields = (
        "id",
        # "model_label",
        # "object_pk",
        # "payload",
        # "context",
        # "status",
        # "attempts",
        "last_error",
        "locked_at",
        "lock_expires_at",
        "created_at",
        "updated_at",
    )
    ordering = ("-created_at",)


@admin.register(AuditDemoRecord)
class AuditDemoRecordAdmin(admin.ModelAdmin):
    """Expose the demo audit model to make manual testing simple."""

    list_display = (
        "id",
        "numeric_value",
        "message",
        "identity_number",
        "created_at",
        "updated_at",
    )
    list_filter = ("created_at",)
    search_fields = ("message", "structured_payload")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)
