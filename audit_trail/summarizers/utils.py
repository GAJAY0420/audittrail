"""Utility helpers for converting diff payloads into natural language."""

from __future__ import annotations

from typing import Any, Dict, List

LOCALE_PHRASES: Dict[str, Dict[str, str]] = {
    "en": {
        "verb_default": "changed",
        "scalar_changed": "{subject} {verb} from {before} to {after}.",
        "scalar_same": "{subject} remained {value}.",
        "m2m_intro": "{subject} updated: {details}.",
        "m2m_added": "added {items}",
        "m2m_removed": "removed {items}",
        "m2m_none": "no membership changes",
    },
    "de": {
        "verb_default": "geändert",
        "scalar_changed": "{subject} wurde von {before} zu {after} {verb}.",
        "scalar_same": "{subject} blieb {value}.",
        "m2m_intro": "{subject} aktualisiert: {details}.",
        "m2m_added": "hinzugefügt {items}",
        "m2m_removed": "entfernt {items}",
        "m2m_none": "keine Änderungen an den Mitgliedschaften",
    },
}


def _resolve_phrases(locale: str) -> Dict[str, str]:
    normalized = (locale or "en").lower()
    return LOCALE_PHRASES.get(normalized, LOCALE_PHRASES["en"])


def _format_value(value: Any) -> str:
    if value is None or value == "":
        return "empty"
    if isinstance(value, dict):
        if {"repr", "pk"}.issubset(value.keys()) or "repr" in value:
            return str(value.get("repr"))
        parts = [f"{key}={_format_value(val)}" for key, val in value.items()]
        return ", ".join(parts)
    if isinstance(value, (list, tuple)):
        formatted = [_format_value(item) for item in value if item is not None]
        return ", ".join(formatted) if formatted else "empty"
    return str(value)


def _format_collection(items: Any) -> str:
    if not items:
        return "none"
    if isinstance(items, list):
        labels: List[str] = []
        for item in items:
            if isinstance(item, dict) and item.get("repr"):
                labels.append(str(item["repr"]))
            else:
                labels.append(_format_value(item))
        return ", ".join(labels)
    return _format_value(items)


def describe_change(
    field_name: str,
    change: Dict[str, Any],
    *,
    verb: str | None = None,
    locale: str = "en",
) -> str:
    """Convert a diff entry into a locale-aware human sentence.

    Args:
        field_name: Registered field name for the change entry.
        change: The structured diff payload for the given field.
        verb: Optional override for the verb describing the change.
        locale: BCP47-style locale code (e.g., "en", "de").

    Returns:
        str: Descriptive sentence tailored to the requested locale.
    """

    if not isinstance(change, dict):
        resolved_phrases = _resolve_phrases(locale)
        verb_text = verb or resolved_phrases["verb_default"]
        return f"{field_name} {verb_text}."

    phrases = _resolve_phrases(locale)
    verb_text = verb or phrases["verb_default"]

    field_label = change.get("label") or field_name
    field_type = change.get("field_type")
    subject = f"{field_label} ({field_type})" if field_type else field_label
    relation = change.get("relation", "field")

    if relation == "many_to_many":
        added = change.get("added", [])
        removed = change.get("removed", [])
        fragments = []
        if added:
            fragments.append(
                phrases["m2m_added"].format(items=_format_collection(added))
            )
        if removed:
            fragments.append(
                phrases["m2m_removed"].format(items=_format_collection(removed))
            )
        if not fragments:
            fragments.append(phrases["m2m_none"])
        details = ", ".join(fragments)
        return phrases["m2m_intro"].format(subject=subject, details=details)

    before = _format_value(change.get("before"))
    after = _format_value(change.get("after"))
    if before == after:
        return phrases["scalar_same"].format(subject=subject, value=after)
    return phrases["scalar_changed"].format(
        subject=subject, verb=verb_text, before=before, after=after
    )
