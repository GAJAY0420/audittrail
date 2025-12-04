from __future__ import annotations

from collections import defaultdict
from typing import DefaultDict, Dict, Iterable, Optional, TYPE_CHECKING, Type

if TYPE_CHECKING:  # pragma: no cover
    from django.db import models


class M2MTracker:
    def __init__(self) -> None:
        self._pending: DefaultDict[str, Dict[str, Dict[str, object]]] = defaultdict(
            lambda: defaultdict(
                lambda: {
                    "add": set(),
                    "remove": set(),
                    "model": None,
                    "label": None,
                }
            )
        )

    def track(
        self,
        *,
        obj_key: str,
        field_name: str,
        action: str,
        pk_set: Iterable[int] | None,
        model: Optional[Type["models.Model"]] = None,
        label: Optional[str] = None,
    ) -> None:
        bucket = self._pending[obj_key][field_name]
        if model is not None:
            bucket["model"] = model
        if label is not None:
            bucket["label"] = label
        if not pk_set:
            return
        target = "add" if action.endswith("add") else "remove"
        bucket[target].update(pk_set)

    def consume(self, obj_key: str) -> Dict[str, Dict[str, object]]:
        return self._pending.pop(obj_key, {})

    def consume_field(self, obj_key: str, field_name: str) -> Dict[str, object]:
        """Remove and return pending changes for a single field."""

        field_bucket = self._pending.get(obj_key)
        if not field_bucket:
            return {}
        payload = field_bucket.pop(field_name, {})
        if not field_bucket:
            self._pending.pop(obj_key, None)
        return payload


tracker = M2MTracker()
