from __future__ import annotations

from types import SimpleNamespace

import pytest

from audit_trail.diffengine import signals


def _make_instance() -> SimpleNamespace:
    return SimpleNamespace(_meta=SimpleNamespace(label="app.Model", many_to_many=()))


@pytest.fixture(name="m2m_config")
def fixture_m2m_config():
    return SimpleNamespace(fields=(), sensitive=(), m2m=("roles",))


def test_m2m_signal_enqueues_event(monkeypatch: pytest.MonkeyPatch, m2m_config):
    instance = _make_instance()
    monkeypatch.setattr(signals, "_resolve_m2m_field", lambda instance, sender: "roles")
    monkeypatch.setattr(signals.registry, "get", lambda label: m2m_config)
    monkeypatch.setattr(signals, "_object_key", lambda instance: "obj-key")
    monkeypatch.setattr(signals, "_get_model_field", lambda instance, field_name: None)
    monkeypatch.setattr(signals.tracker, "track", lambda **kwargs: None)
    monkeypatch.setattr(
        signals.tracker,
        "consume_field",
        lambda obj_key, field_name: {
            "add": {1},
            "remove": set(),
            "model": SimpleNamespace(__name__="Role"),
        },
    )
    monkeypatch.setattr(
        signals,
        "_serialize_m2m_change",
        lambda field_name, model_field, payload: {
            "field": field_name,
            "added": sorted(payload["add"]),
        },
    )
    captured: list[tuple[dict, str]] = []
    monkeypatch.setattr(
        signals,
        "_enqueue",
        lambda inst, diff, event_type: captured.append((diff, event_type)),
    )

    signals.audittrail_m2m(
        sender=object(),
        instance=instance,
        action="post_add",
        reverse=False,
        model=SimpleNamespace(),
        pk_set={1},
    )

    assert captured
    diff, event_type = captured[0]
    assert diff["roles"]["added"] == [1]
    assert event_type == "updated"


def test_m2m_signal_noop_when_tracker_empty(
    monkeypatch: pytest.MonkeyPatch, m2m_config
):
    instance = _make_instance()
    monkeypatch.setattr(signals, "_resolve_m2m_field", lambda instance, sender: "roles")
    monkeypatch.setattr(signals.registry, "get", lambda label: m2m_config)
    monkeypatch.setattr(signals.tracker, "track", lambda **kwargs: None)
    monkeypatch.setattr(signals, "_object_key", lambda instance: "obj-key")
    monkeypatch.setattr(signals, "_get_model_field", lambda instance, field_name: None)
    monkeypatch.setattr(signals.tracker, "consume_field", lambda *args, **kwargs: {})
    events: list[object] = []
    monkeypatch.setattr(signals, "_enqueue", lambda *args, **kwargs: events.append(1))

    signals.audittrail_m2m(
        sender=object(),
        instance=instance,
        action="post_add",
        reverse=False,
        model=SimpleNamespace(),
        pk_set={1},
    )

    assert events == []
