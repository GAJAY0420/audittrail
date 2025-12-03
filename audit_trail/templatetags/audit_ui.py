"""Custom template filters for rendering audit trail UI elements."""

from __future__ import annotations

import re
from typing import Final

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

_CODE_PATTERN: Final = re.compile(r"`([^`]+)`")
_BOLD_PATTERN: Final = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC_PATTERN: Final = re.compile(r"(?<!\*)\*([^*]+?)\*(?!\*)")


def _apply_code_spans(value: str) -> str:
    return _CODE_PATTERN.sub(r"<code>\1</code>", value)


def _apply_bold_spans(value: str) -> str:
    return _BOLD_PATTERN.sub(r"<strong>\1</strong>", value)


def _apply_italic_spans(value: str) -> str:
    return _ITALIC_PATTERN.sub(r"<em>\1</em>", value)


@register.filter(name="rich_summary")
def render_rich_summary(value: str | None) -> str:
    """Render a lightweight Markdown/inline-code summary as safe HTML."""

    if not value:
        return ""

    escaped = escape(value)
    formatted = _apply_code_spans(escaped)
    formatted = _apply_bold_spans(formatted)
    formatted = _apply_italic_spans(formatted)
    formatted = formatted.replace("\n", "<br>")
    return mark_safe(formatted)
