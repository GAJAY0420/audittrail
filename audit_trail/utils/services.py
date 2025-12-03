from __future__ import annotations

from typing import Any, Dict

from django.utils import timezone

from audit_trail.summarizers import summarize


def build_event(
    instance, changes: Dict[str, Any], *, context: Dict[str, Any]
) -> Dict[str, Any]:
    timestamp = timezone.now().isoformat()
    summary = summarize(changes)
    return {
        "model": instance._meta.label,  # type: ignore[attr-defined]
        "object_id": str(instance.pk),
        "timestamp": timestamp,
        "diff": changes,
        "actor": context.get("actor"),
        "context": context,
        "summary": summary,
    }
