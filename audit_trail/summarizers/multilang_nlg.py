from __future__ import annotations

from typing import Any, Dict

from .utils import describe_change

TRANSLATIONS = {
    "en": "changed",
    "hi": "badla",
    "te": "marpadi",
    "de": "geandert",
    "ms": "berubah",
    "zh": "變更",
}


def summarize(diff: Dict[str, Dict[str, Any]], *, locale: str = "en") -> str:
    verb = TRANSLATIONS.get(locale, TRANSLATIONS["en"])
    parts = [
        describe_change(field, payload, verb=verb, locale=locale)
        for field, payload in diff.items()
    ]
    return "; ".join(parts)
