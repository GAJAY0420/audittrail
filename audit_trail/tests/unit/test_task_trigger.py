"""Unit tests for the task execution helper that toggles Celery usage."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from audit_trail.tasks import trigger_outbox_dispatch


def test_trigger_outbox_dispatch_async(settings):
    settings.AUDITTRAIL_USE_CELERY = True
    with patch("audit_trail.tasks.dispatch_outbox.apply_async") as apply_async:
        async_result = MagicMock()
        apply_async.return_value = async_result
        result = trigger_outbox_dispatch(batch_size=42)
        apply_async.assert_called_once_with(args=(42,))
        assert result is async_result


def test_trigger_outbox_dispatch_sync(settings):
    settings.AUDITTRAIL_USE_CELERY = False
    with patch("audit_trail.tasks.dispatch_outbox.apply") as apply_sync, patch(
        "audit_trail.tasks._run_dispatch"
    ) as run_dispatch:
        eager_result = MagicMock()
        eager_result.get.return_value = 7
        apply_sync.return_value = eager_result
        result = trigger_outbox_dispatch(batch_size=15)
        apply_sync.assert_called_once_with(args=(15,))
        eager_result.get.assert_called_once_with()
        run_dispatch.assert_not_called()
        assert result == 7


def test_trigger_outbox_dispatch_sync_fallback(settings):
    settings.AUDITTRAIL_USE_CELERY = False
    with patch(
        "audit_trail.tasks.dispatch_outbox.apply", side_effect=RuntimeError("redis")
    ) as apply_sync, patch(
        "audit_trail.tasks._run_dispatch", return_value=5
    ) as run_dispatch:
        result = trigger_outbox_dispatch(batch_size=3)

    apply_sync.assert_called_once_with(args=(3,))
    run_dispatch.assert_called_once_with(3)
    assert result == 5
