from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Sequence

from django.conf import settings


@dataclass
class ModelRegistration:
    dotted_path: str
    fields: Sequence[str]
    sensitive: Sequence[str] = field(default_factory=tuple)
    m2m: Sequence[str] = field(default_factory=tuple)


def load_registry_settings() -> Dict[str, ModelRegistration]:
    configured = getattr(settings, "AUDITTRAIL_MODELS", {})
    normalized: Dict[str, ModelRegistration] = {}
    for dotted_path, payload in configured.items():
        normalized[dotted_path] = ModelRegistration(
            dotted_path=dotted_path,
            fields=payload.get("fields", ()),
            sensitive=payload.get("sensitive", ()),
            m2m=payload.get("m2m", ()),
        )
    return normalized
