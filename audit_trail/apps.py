from django.apps import AppConfig


class AuditTrailConfig(AppConfig):
    name = "audit_trail"
    verbose_name = "Audit Trail"

    def ready(self) -> None:
        """Initialize signal handlers, registry state, and demo fixtures."""

        # Lazily import to avoid premature Django model loading.
        from .diffengine import signals  # noqa: F401  # pylint: disable=unused-import
        from .registry.registry import registry  # noqa: F401
        from . import admin  # noqa: F401  # ensure admin registrations are loaded

        registry.load_from_settings()
        self._register_demo_model()

    def _register_demo_model(self) -> None:
        """Optionally register the demo model so audit events fire automatically."""

        from django.conf import settings

        from .registry.registry import register_model

        if getattr(settings, "AUDITTRAIL_ENABLE_DEMO_MODEL", True):
            register_model(
                "audit_trail.AuditDemoRecord",
                fields=("numeric_value", "message", "structured_payload"),
                sensitive=("identity_number",),
            )
