"""Project package enabling standalone execution of tiger_audit_trail."""

from __future__ import annotations

from .celery import app as celery_app

__all__ = ["celery_app"]
