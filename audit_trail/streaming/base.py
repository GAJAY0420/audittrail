"""Shared streaming publisher abstractions used across providers."""

from __future__ import annotations

import importlib
from typing import Any, Dict

from django.conf import settings


class BaseStreamPublisher:
    """Base class for streaming adapters that publish audit events."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the stream publisher with the given configuration.

        Args:
            config: Provider-specific configuration values.
        """
        self.config = config

    def publish(self, event: Dict[str, Any]) -> None:  # pragma: no cover - interface
        """Publish an event to the stream.

        Args:
            event: Fully serialized audit event ready for downstream processing.
        """
        raise NotImplementedError


def get_stream_publisher() -> BaseStreamPublisher:
    """Instantiate the configured stream publisher implementation.

    Returns:
        BaseStreamPublisher: The dynamically loaded publisher instance.

    Raises:
        RuntimeError: If streaming is disabled in the Django settings.
        ImportError: If the configured module path cannot be imported.
        AttributeError: If the configured class does not exist on the module.
    """
    if not getattr(settings, "AUDITTRAIL_STREAMING_ENABLED", False):
        raise RuntimeError("Streaming disabled")
    backend_path = getattr(
        settings,
        "AUDITTRAIL_STREAM_PROVIDER",
        "audit_trail.streaming.kafka.KafkaPublisher",
    )
    module_path, class_name = backend_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    publisher_class = getattr(module, class_name)
    config = getattr(settings, "AUDITTRAIL_STREAM_CONFIG", {})
    return publisher_class(config)
