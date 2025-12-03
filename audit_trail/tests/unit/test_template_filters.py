"""Tests for UI template filters."""

from __future__ import annotations

from audit_trail.templatetags import audit_ui


def test_render_rich_summary_handles_markdown() -> None:
    summary = (
        '**Audit Log Update** The message was updated from *"Foo"* to *"Bar"*.'
        " Additionally, the structured payload now includes `sent_to_dynamo=True`."
    )
    rendered = audit_ui.render_rich_summary(summary)
    assert "<strong>Audit Log Update</strong>" in rendered
    assert "<em>&quot;Foo&quot;</em>" in rendered
    assert "<code>sent_to_dynamo=True</code>" in rendered


def test_render_rich_summary_returns_empty_for_none() -> None:
    assert audit_ui.render_rich_summary(None) == ""
