"""Mixins that enable audit trail integration on Django models."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict

from django.db import models

from audit_trail.diffengine import signals as audit_signals
from audit_trail.registry.registry import registry


class AuditMixin(models.Model):
    """Provide convenience helpers for audit trail enabled models."""

    class Meta:
        abstract = True

    def get_audit_context(self) -> Dict[str, Any]:
        """Return per-instance metadata for audit entries.

        Returns:
            dict: Additional context (e.g., actor, IP address) to store with the audit event.
        """

        return {}

    @property
    def audit_object_id(self) -> str:
        """Generate a deterministic object identifier for audit records.

        Returns:
            str: A unique key combining the model label and primary key.
        """

        return f"{self._meta.label_lower}:{self.pk}"  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # Django lifecycle overrides
    # ------------------------------------------------------------------
    def save(self, *args, **kwargs):  # noqa: ANN001
        should_track = self._is_audited()
        created = self._state.adding  # type: ignore[attr-defined]
        if not should_track:
            return super().save(*args, **kwargs)
        audit_signals.record_pre_save(self)
        with self._mixin_guard():
            result = super().save(*args, **kwargs)
        audit_signals.record_post_save(self, created=created)
        return result

    def delete(self, *args, **kwargs):  # noqa: ANN001
        should_track = self._is_audited()
        if not should_track:
            return super().delete(*args, **kwargs)
        with self._mixin_guard():
            result = super().delete(*args, **kwargs)
        audit_signals.record_post_delete(self)
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _is_audited(self) -> bool:
        return bool(registry.get(self._meta.label))

    @contextmanager
    def _mixin_guard(self):
        setattr(self, "_audit_trail_mixin_active", True)
        try:
            yield
        finally:
            setattr(self, "_audit_trail_mixin_active", False)
