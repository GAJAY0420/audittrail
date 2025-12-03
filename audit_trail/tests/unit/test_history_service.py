"""Tests for the history service helpers."""

from __future__ import annotations

import pytest

from audit_trail.history import service
from audit_trail.history.service import HistoryQueryError


class DummyBackend:
    """Simple in-memory backend used to capture calls and return canned events."""

    def __init__(self, events: list[dict[str, object]]):
        self.events = events
        self.object_calls: list[tuple[str, str, int, str | None]] = []
        self.user_calls: list[tuple[str, int, str | None]] = []

    def fetch_object_events(
        self,
        *,
        model: str,
        object_id: str,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[dict[str, object]], str | None]:
        self.object_calls.append((model, object_id, limit, cursor))
        return self.events, None

    def fetch_user_events(
        self,
        *,
        user_id: str,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[dict[str, object]], str | None]:
        self.user_calls.append((user_id, limit, cursor))
        return self.events, None


@pytest.fixture()
def monkey_backend(monkeypatch: pytest.MonkeyPatch) -> DummyBackend:
    events = [
        {
            "event_id": "evt-1",
            "model": "app.Model",
            "object_id": "42",
            "timestamp": "2024-01-01T00:00:00Z",
            "summary": "Status updated",
            "event_type": "updated",
            "actor": {"id": "7", "username": "alice"},
            "diff": {"status": {"before": "pending", "after": "approved"}},
        }
    ]
    backend = DummyBackend(events)
    monkeypatch.setattr(service, "get_storage_backend", lambda: backend)
    return backend


def test_fetch_history_requires_filters(monkey_backend: DummyBackend) -> None:
    with pytest.raises(HistoryQueryError):
        service.fetch_history(model=None, object_id=None, user_id=None)


def test_fetch_history_object_flow(monkey_backend: DummyBackend) -> None:
    result = service.fetch_history(model="app.Model", object_id="42", user_id=None)
    assert len(result.events) == 1
    assert result.events[0].summary == "Status updated"
    assert monkey_backend.object_calls == [("app.Model", "42", 25, None)]


def test_fetch_history_user_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    events = [
        {
            "event_id": "evt-1",
            "model": "app.Model",
            "object_id": "42",
            "timestamp": "2024-01-01T00:00:00Z",
            "summary": "Status updated",
            "event_type": "updated",
            "actor": {"id": "7"},
            "diff": {},
        },
        {
            "event_id": "evt-2",
            "model": "app.Model",
            "object_id": "42",
            "timestamp": "2024-01-02T00:00:00Z",
            "summary": "Status updated",
            "event_type": "updated",
            "actor": {"id": "8"},
            "diff": {},
        },
    ]
    backend = DummyBackend(events)
    monkeypatch.setattr(service, "get_storage_backend", lambda: backend)
    result = service.fetch_history(
        model="app.Model", object_id="42", user_id="7", limit=10
    )
    assert len(result.events) == 1
    assert result.events[0].actor["id"] == "7"
