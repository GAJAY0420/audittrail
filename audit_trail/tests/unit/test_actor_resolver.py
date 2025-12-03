"""Validate resolving actors via middleware callables."""

from __future__ import annotations

from django.test import override_settings

from audit_trail.utils.actor import resolve_actor_from_settings


@override_settings(
    AUDITTRAIL_ACTOR_RESOLVER="audit_trail.tests.unit.actor_resolver_fixtures.return_username"
)
def test_actor_resolver_returns_string() -> None:
    """String-returning resolvers should be surfaced verbatim."""

    assert resolve_actor_from_settings() == {"username": "middleware-user"}


@override_settings(
    AUDITTRAIL_ACTOR_RESOLVER="audit_trail.tests.unit.actor_resolver_fixtures.return_user_object"
)
def test_actor_resolver_handles_user_objects() -> None:
    """User-like objects should be coerced via ``get_username``."""

    assert resolve_actor_from_settings() == {
        "username": "resolver-user",
        "email": "user@example.com",
        "id": 7,
    }


@override_settings(AUDITTRAIL_ACTOR_RESOLVER="does.not.exist")
def test_actor_resolver_handles_import_errors() -> None:
    """Import failures must not raise and should return ``None``."""

    assert resolve_actor_from_settings() is None
