"""Helpers for querying audit history from the configured storage backend."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from audit_trail.storage.backends.base import get_storage_backend


@dataclass
class HistoryEvent:
    """Normalized representation of an audit history entry."""

    event_id: str
    model: str
    object_id: str
    timestamp: str
    summary: str
    event_type: str
    actor: Dict[str, Any] | None
    diff: Dict[str, Any]
    raw: Dict[str, Any]


@dataclass
class HistoryResult:
    """Container for a paginated history response."""

    events: List[HistoryEvent]
    next_cursor: Optional[str]


class HistoryQueryError(ValueError):
    """Raised when the supplied filters are invalid."""


def fetch_history(
    *,
    model: str | None,
    object_id: str | None,
    user_id: str | None,
    limit: int = 25,
    cursor: str | None = None,
) -> HistoryResult:
    """Return paginated history entries based on the provided filters."""

    if not object_id and not user_id:
        raise HistoryQueryError(
            "Provide either an object_id or user_id to fetch history."
        )
    if object_id and not model:
        raise HistoryQueryError("Model label is required when querying by object.")

    backend = get_storage_backend()
    backend_limit = max(1, min(200, limit))

    if object_id:
        raw_events, next_cursor = backend.fetch_object_events(
            model=model,
            object_id=object_id,
            limit=backend_limit,
            cursor=cursor,
        )
    else:
        raw_events, next_cursor = backend.fetch_user_events(
            user_id=user_id or "anonymous",
            limit=backend_limit,
            cursor=cursor,
        )

    events: List[HistoryEvent] = []
    for raw in raw_events:
        normalized = _normalize_event(raw)
        if user_id and object_id and not _matches_user(normalized.actor, user_id):
            continue
        if user_id and not object_id and not _matches_user(normalized.actor, user_id):
            continue
        events.append(normalized)

    return HistoryResult(events=events, next_cursor=next_cursor)


def _normalize_event(raw: Dict[str, Any]) -> HistoryEvent:
    actor = raw.get("actor") or (raw.get("context") or {}).get("actor")
    summary = raw.get("summary") or (raw.get("context") or {}).get("summary")
    event_type = raw.get("event_type") or (raw.get("context") or {}).get(
        "event_type", "updated"
    )
    event_id = (
        raw.get("event_id")
        or raw.get("eventId")
        or raw.get("id")
        or raw.get("sk")
        or "unknown"
    )
    timestamp = raw.get("timestamp") or raw.get("created_at") or raw.get("sk", "")
    model = raw.get("model") or raw.get("model_label") or "unknown"
    object_id = (
        raw.get("object_id") or raw.get("objectPk") or raw.get("object_pk") or "unknown"
    )
    diff = raw.get("diff") or raw.get("changes") or {}

    return HistoryEvent(
        event_id=str(event_id),
        model=str(model),
        object_id=str(object_id),
        timestamp=str(timestamp),
        summary=str(summary or f"{event_type.title()} {model}"),
        event_type=str(event_type),
        actor=actor,
        diff=diff if isinstance(diff, dict) else {},
        raw=raw,
    )


def _matches_user(actor_payload: Optional[Dict[str, Any]], user_id: str | None) -> bool:
    if not user_id:
        return True
    if not actor_payload:
        return False
    return str(actor_payload.get("id")) == str(user_id)
