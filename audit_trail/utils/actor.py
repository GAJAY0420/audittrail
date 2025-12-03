"""Resolve audit actors using middleware-provided helpers."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any, Callable, Dict, Optional

from django.conf import settings
from django.utils.module_loading import import_string

LOGGER = logging.getLogger(__name__)
ActorResolver = Callable[[], Any]
ActorPayload = Dict[str, Any]


def _call_maybe(value: Any) -> Any:
    """Invoke callables while leaving plain values untouched."""

    return value() if callable(value) else value


def _serialize_value(value: Any) -> Any:
    """Normalize values so they are safe for JSON serialization."""

    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, (int, float, bool)):
        return value
    return str(value)


def _assign(actor: ActorPayload, key: str, value: Any) -> None:
    normalized = _serialize_value(_call_maybe(value))
    if normalized is None:
        return
    actor.setdefault(key, normalized)


def _populate_from_mapping(value: Mapping[str, Any]) -> Optional[ActorPayload]:
    actor: ActorPayload = {}
    for key, raw in value.items():
        normalized = _serialize_value(_call_maybe(raw))
        if normalized is None:
            continue
        actor[str(key)] = normalized
    if actor and "username" not in actor:
        fallback = actor.get("email") or actor.get("name") or actor.get("id")
        if fallback is not None:
            actor.setdefault("username", fallback)
    return actor


def format_actor_payload(value: Any) -> Optional[ActorPayload]:
    """Attempt to normalize arbitrary resolver outputs into a dict payload."""

    if value is None:
        return {}
    if isinstance(value, Mapping):
        return _populate_from_mapping(value)
    actor: ActorPayload = {}
    if isinstance(value, str):
        normalized = _serialize_value(value)
        if normalized:
            actor["username"] = normalized
        return actor

    for attr in ("get_username", "username"):
        candidate = getattr(value, attr, None)
        if candidate is not None:
            _assign(actor, "username", candidate)
    for attr in ("get_full_name", "full_name"):
        candidate = getattr(value, attr, None)
        if candidate is not None:
            _assign(actor, "name", candidate)
    email_attr = getattr(value, "email", None)
    if email_attr is not None:
        _assign(actor, "email", email_attr)
    for attr in ("pk", "id"):
        candidate = getattr(value, attr, None)
        if candidate is not None:
            _assign(actor, "id", candidate)

    if not actor:
        fallback = _serialize_value(value)
        if fallback is not None:
            actor["username"] = fallback

    return actor


def resolve_actor_from_settings() -> Optional[ActorPayload]:
    """Return actor metadata using ``AUDITTRAIL_ACTOR_RESOLVER`` when set.

    The resolver must be a dotted path to a callable that accepts no arguments and
    returns either:

    * A ``dict`` with actor metadata (e.g., ``{"username": "alice"}``).
    * A string identifier (stored under ``username``).
    * A user-like object exposing ``get_username``/``username``/``email``/``id``.

    Errors are logged and surfaced as ``None`` so that audit capture never fails due
    to misconfiguration.
    """

    path = getattr(settings, "AUDITTRAIL_ACTOR_RESOLVER", None)
    if not path:
        return None
    try:
        resolver: ActorResolver = import_string(path)
    except Exception:  # pragma: no cover - defensive guard
        LOGGER.warning("Unable to import AUDITTRAIL_ACTOR_RESOLVER '%s'", path)
        return None
    try:
        raw_actor = resolver()
    except Exception:  # pragma: no cover - defensive guard
        LOGGER.warning("Actor resolver '%s' raised an error", path)
        return None
    return format_actor_payload(raw_actor)
