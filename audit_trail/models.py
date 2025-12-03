"""Demo data models used to exercise the audit trail pipeline."""

from __future__ import annotations

from typing import Any, Mapping

from django.db import models
from django.utils import timezone

from audit_trail.diffengine.mixins import AuditMixin


class AuditDemoRecordManager(models.Manager["AuditDemoRecord"]):
    """Helper manager that streamlines the creation of demo audit records."""

    def create_demo_record(
        self,
        *,
        number: int,
        message: str,
        payload: Mapping[str, Any] | None = None,
        identity_number: str = "",
    ) -> "AuditDemoRecord":
        """Persist a single demo record with the provided content.

        Args:
            number: Numeric identifier that will be stored in the integer field.
            message: Human-readable text that is written to the text field.
            payload: Optional JSON payload to merge into the structured field.

        Returns:
            AuditDemoRecord: The saved instance that triggered an audit event.
        """

        structured_payload: dict[str, Any] = {"ordinal": number, "message": message}
        if payload:
            structured_payload.update(payload)
        record = self.model(
            numeric_value=number,
            message=message,
            structured_payload=structured_payload,
            identity_number=identity_number,
        )
        record.full_clean()
        record.save()
        return record

    def seed_records(
        self,
        *,
        count: int,
        prefix: str = "Sample audit event",
        base_payload: Mapping[str, Any] | None = None,
        starting_number: int = 1,
        identity_number: str = "ID-{number:05d}",
    ) -> list["AuditDemoRecord"]:
        """Create multiple demo records to batch-generate audit events.

        Args:
            count: Number of records to generate.
            prefix: Text prefix used when building the message for each record.
            base_payload: Optional JSON fragment merged into every payload.
            starting_number: Initial integer value that increments per record.
            identity_number: Unique identity number pattern for each record.

        Returns:
            list[AuditDemoRecord]: All saved demo records for further inspection.
        """

        if count < 1:
            return []
        base_payload_dict = dict(base_payload or {})
        created: list[AuditDemoRecord] = []
        for offset in range(count):
            number = starting_number + offset
            message = f"{prefix} #{number}"
            payload = dict(base_payload_dict)
            payload.update({"ordinal": number, "label": message})
            identity_number = identity_number
            created.append(
                self.create_demo_record(
                    number=number,
                    message=message,
                    payload=payload,
                    identity_number=identity_number,
                )
            )
        return created


class AuditDemoRecord(AuditMixin):
    """Simple auditable model with numeric, text, and JSON fields."""

    numeric_value = models.IntegerField()
    message = models.TextField()
    structured_payload = models.JSONField(default=dict)
    identity_number = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AuditDemoRecordManager()

    class Meta:
        verbose_name = "Audit Demo Record"
        verbose_name_plural = "Audit Demo Records"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        """Return a concise human-readable identifier for admin listings."""

        preview = (
            (self.message[:29] + "...") if len(self.message) > 32 else self.message
        )
        return f"{self.numeric_value}: {preview}"
