"""Base classes and helpers for configuring storage backends."""

from __future__ import annotations

import importlib
from typing import Any, Dict, Iterable, List, Tuple

from django.conf import settings


class BaseStorageBackend:
    """Abstract interface for persisting audit payloads to a final store."""

    def __init__(self, *, config: Dict[str, Any]):
        """Initialize backend configuration.

        Args:
            config: Dictionary of backend specific configuration values.
        """

        self.config = config

    def store_event(
        self, payload: Dict[str, Any]
    ) -> None:  # pragma: no cover - interface
        """Persist a single payload.

        Args:
            payload: Serialized audit event to persist.
        """

        raise NotImplementedError

    def bulk_store(
        self, payloads: Iterable[Dict[str, Any]]
    ) -> None:  # pragma: no cover - optional override
        """Persist multiple payloads, defaulting to iterative storage.

        Args:
            payloads: Iterable of serialized audit events.
        """

        for payload in payloads:
            self.store_event(payload)

    # ------------------------------------------------------------------
    # History queries
    # ------------------------------------------------------------------

    def fetch_object_events(
        self,
        *,
        model: str | None,
        object_id: str,
        limit: int = 50,
        cursor: str | None = None,
    ) -> Tuple[List[Dict[str, Any]], str | None]:  # pragma: no cover - interface
        """Return events for a specific object ordered newest first."""

        raise NotImplementedError

    def fetch_user_events(
        self,
        *,
        user_id: str,
        limit: int = 50,
        cursor: str | None = None,
    ) -> Tuple[List[Dict[str, Any]], str | None]:  # pragma: no cover - interface
        """Return events initiated by a specific user ordered newest first."""

        raise NotImplementedError


def get_storage_backend() -> BaseStorageBackend:
    """Instantiate the configured storage backend."""

    backend_path = getattr(
        settings,
        "AUDITTRAIL_STORAGE_BACKEND",
        "audit_trail.storage.backends.dynamo.DynamoStorageBackend",
    )
    module_path, class_name = backend_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    backend_class = getattr(module, class_name)
    config = getattr(settings, "AUDITTRAIL_STORAGE_CONFIG", {})
    return backend_class(config=config)
