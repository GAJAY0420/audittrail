"""Celery tasks powering the audit trail outbox dispatcher."""

from __future__ import annotations

import logging
from typing import Optional

from celery import shared_task
from celery.result import AsyncResult
from django.conf import settings

from audit_trail.storage.backends.base import get_storage_backend
from audit_trail.storage.outbox.models import AuditEventOutbox
from audit_trail.streaming import base as streaming_base

LOGGER = logging.getLogger(__name__)


def _run_dispatch(batch_size: int) -> int:
    """Execute the outbox dispatch loop synchronously."""

    backend = get_storage_backend()
    publisher: Optional[streaming_base.BaseStreamPublisher] = None
    if getattr(settings, "AUDITTRAIL_STREAMING_ENABLED", False):
        publisher = streaming_base.get_stream_publisher()

    processed = 0
    entries = AuditEventOutbox.objects.acquire_batch(batch_size=batch_size)
    for entry in entries:
        try:
            backend.store_event(entry.payload)
            if publisher:
                publisher.publish(entry.payload)
            entry.mark_sent()
            processed += 1
        except Exception as exc:  # pragma: no cover - logged by Celery
            entry.mark_failure(str(exc))
            LOGGER.error("Error dispatching outbox entry %s: %s", entry.id, exc)
            raise
    return processed


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def dispatch_outbox(self, batch_size: int = 100) -> int:
    return _run_dispatch(batch_size)


def trigger_outbox_dispatch(batch_size: int = 100) -> int | AsyncResult:
    """Execute the dispatcher inline or enqueue it on Celery.

    Args:
        batch_size: Maximum number of events to process when the dispatcher runs.

    Returns:
        Either the integer count of processed events when running inline or the
        ``AsyncResult`` returned by Celery when the task is enqueued.
    """

    if getattr(settings, "AUDITTRAIL_USE_CELERY", False):
        return dispatch_outbox.apply_async(args=(batch_size,))

    try:
        eager_result = dispatch_outbox.apply(args=(batch_size,))
        return int(eager_result.get())
    except Exception as exc:  # pragma: no cover - fallback path
        LOGGER.debug(
            "dispatch_outbox.apply failed (%s); falling back to direct call", exc
        )
        return _run_dispatch(batch_size)
