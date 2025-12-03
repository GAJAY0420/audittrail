from __future__ import annotations

from typing import Any, Dict

from .utils import describe_change


def summarize(diff: Dict[str, Dict[str, Any]]) -> str:
    parts = [describe_change(field, payload) for field, payload in diff.items()]
    filtered = [part for part in parts if part]
    return "; ".join(filtered) or "No material changes recorded."
