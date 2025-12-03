from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Iterable, Optional

from .config_loader import ModelRegistration, load_registry_settings


class Registry:
    """
    Central registry for audit trail model configurations.

    Manages the registration of models, their tracked fields, sensitive fields,
    and many-to-many relationships.
    """

    def __init__(self) -> None:
        self._registry: Dict[str, ModelRegistration] = {}

    def register(
        self,
        dotted_path: str,
        *,
        fields: Iterable[str],
        sensitive: Optional[Iterable[str]] = None,
        m2m: Optional[Iterable[str]] = None,
    ) -> None:
        """
        Register a model for auditing.

        Args:
            dotted_path: The Python path to the model (e.g., 'app.Model').
            fields: List of field names to track changes for.
            sensitive: List of field names to mask in the audit log.
            m2m: List of ManyToManyField names to track.
        """
        normalized = ModelRegistration(
            dotted_path=dotted_path,
            fields=tuple(fields),
            sensitive=tuple(sensitive or ()),
            m2m=tuple(m2m or ()),
        )
        self._registry[dotted_path] = normalized

    def get(self, dotted_path: str) -> Optional[ModelRegistration]:
        """
        Retrieve the configuration for a registered model.

        Args:
            dotted_path: The Python path to the model.

        Returns:
            ModelRegistration: The configuration object, or None if not registered.
        """
        return self._registry.get(dotted_path)

    def all(self) -> Dict[str, Dict[str, Iterable[str]]]:
        return {key: asdict(value) for key, value in self._registry.items()}

    def clear(self) -> None:
        self._registry.clear()

    def load_from_settings(self) -> None:
        configured = load_registry_settings()
        for dotted_path, registration in configured.items():
            self._registry.setdefault(dotted_path, registration)


registry = Registry()
register_model = registry.register
