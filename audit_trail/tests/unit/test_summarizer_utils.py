from __future__ import annotations

from audit_trail.summarizers.utils import describe_change


def test_describe_change_includes_field_type():
    change = {
        "field": "owner",
        "field_type": "ForeignKey",
        "relation": "foreign_key",
        "before": {"repr": "Alice"},
        "after": {"repr": "Bob"},
    }
    summary = describe_change("owner", change, locale="en")
    assert "ForeignKey" in summary
    assert "Alice" in summary and "Bob" in summary


def test_describe_change_handles_many_to_many():
    change = {
        "field": "tags",
        "field_type": "ManyToManyField",
        "relation": "many_to_many",
        "added": [{"repr": "Critical"}, {"repr": "VIP"}],
        "removed": [{"repr": "Legacy"}],
    }
    summary = describe_change("tags", change, locale="en")
    assert "added Critical" in summary
    assert "removed Legacy" in summary


def test_describe_change_translates_to_german():
    change = {
        "field": "owner",
        "field_type": "ForeignKey",
        "relation": "foreign_key",
        "before": {"repr": "Alice"},
        "after": {"repr": "Bob"},
    }
    summary = describe_change("owner", change, locale="de")
    assert "wurde von" in summary or "geändert" in summary
    assert "Alice" in summary and "Bob" in summary
