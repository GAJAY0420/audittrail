"""Utility helpers for cleaning the audit outbox table."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from .models import AuditEventOutbox


def purge_sent_entries(max_age_hours: int = 24) -> int:
    """Delete sent entries that are older than the configured TTL.

    Args:
        max_age_hours: Age threshold in hours for cleanup.

    Returns:
        int: Number of rows removed from the outbox.
    """

    threshold = timezone.now() - timedelta(hours=max_age_hours)
    deleted, _ = AuditEventOutbox.objects.filter(
        status="sent", updated_at__lt=threshold
    ).delete()
    return deleted


def release_stuck_entries() -> int:
    """Release outbox entries whose locks have expired.

    Returns:
        int: Number of entries unlocked.
    """

    return AuditEventOutbox.objects.release_expired_locks()
