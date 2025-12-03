"""Database models representing the audit trail transactional outbox."""

from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone

from .managers import AuditEventOutboxManager


class AuditEventOutbox(models.Model):
    """Outbox record that buffers audit events for asynchronous delivery."""

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("locked", "Locked"),
        ("sent", "Sent"),
        ("failed", "Failed"),
        ("dlq", "Dead Letter"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model_label = models.CharField(max_length=255)
    object_pk = models.CharField(max_length=255)
    payload = models.JSONField()
    context = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending")
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    lock_expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AuditEventOutboxManager()

    class Meta:
        verbose_name = "Audit Event Outbox"
        verbose_name_plural = "Audit Event Outboxes"
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["model_label", "object_pk"]),
        ]

    def mark_sent(self) -> None:
        """Mark the entry as successfully delivered downstream."""

        self.status = "sent"
        self.save(update_fields=["status", "updated_at"])

    def mark_failure(self, error: str, *, max_attempts: int = 5) -> None:
        """Increment failure counters and set DLQ status when retries are exhausted.

        Args:
            error: The error message observed during processing.
            max_attempts: Maximum retry attempts before the event is DLQ'd.
        """

        self.attempts += 1
        self.last_error = error
        if self.attempts >= max_attempts:
            self.status = "dlq"
        else:
            self.status = "pending"
            self.locked_at = None
            self.lock_expires_at = None
        self.save(
            update_fields=[
                "status",
                "attempts",
                "last_error",
                "locked_at",
                "lock_expires_at",
                "updated_at",
            ]
        )
