"""Custom manager and queryset for the audit trail outbox."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List, TYPE_CHECKING

from django.db import models, transaction
from django.utils import timezone

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .models import AuditEventOutbox


class AuditEventOutboxQuerySet(models.QuerySet):
    """Queryset helpers for filtering audit outbox entries."""

    def pending(self) -> "AuditEventOutboxQuerySet":
        """Return entries queued for processing."""

        return self.filter(status="pending")

    def locked(self) -> "AuditEventOutboxQuerySet":
        """Return entries currently locked by a worker."""

        return self.filter(status="locked")


class AuditEventOutboxManager(models.Manager):
    """Manager providing enqueue and batching operations for the outbox."""

    def get_queryset(self) -> AuditEventOutboxQuerySet:  # type: ignore[override]
        """Return the audit-specific queryset."""

        return AuditEventOutboxQuerySet(self.model, using=self._db)

    def pending(self) -> AuditEventOutboxQuerySet:
        """Shortcut to fetch pending entries."""

        return self.get_queryset().pending()

    def locked(self) -> AuditEventOutboxQuerySet:
        """Shortcut to fetch locked entries."""

        return self.get_queryset().locked()

    def enqueue(
        self,
        *,
        instance: models.Model,
        payload: Dict[str, Any],
        context: Dict[str, Any],
    ) -> None:
        """Persist a new audit outbox entry for the given model instance.

        Args:
            instance: The model instance that produced the audit event.
            payload: Serialized audit payload destined for downstream storage.
            context: Additional context metadata stored alongside the payload.
        """

        event_outbox = self.create(
            model_label=instance._meta.label,  # type: ignore[attr-defined]
            object_pk=str(instance.pk),
            payload=payload,
            status="pending",
            context=context,
        )
        payload["event_id"] = str(event_outbox.pk)
        event_outbox.payload = payload
        event_outbox.save(update_fields=["payload"])

    def acquire_batch(
        self, batch_size: int = 100, lock_for: int = 60
    ) -> List["AuditEventOutbox"]:
        """Lock and return a batch of pending entries for processing.

        Args:
            batch_size: Maximum number of entries to fetch.
            lock_for: Lock duration in seconds to prevent duplicate processing.

        Returns:
            list[AuditEventOutbox]: The locked entries ready for dispatch.
        """

        now = timezone.now()
        with transaction.atomic():
            entries = list(
                self.pending()
                .select_for_update(skip_locked=True)
                .order_by("created_at")[:batch_size]
            )
            for entry in entries:
                entry.status = "locked"
                entry.locked_at = now
                entry.lock_expires_at = now + timedelta(seconds=lock_for)
                entry.save(update_fields=["status", "locked_at", "lock_expires_at"])
        return entries

    def release_expired_locks(self) -> int:
        """Release locks that have exceeded their TTL.

        Returns:
            int: Number of entries moved back to the pending state.
        """

        now = timezone.now()
        return (
            self.locked()
            .filter(lock_expires_at__lt=now)
            .update(status="pending", locked_at=None, lock_expires_at=None)
        )
