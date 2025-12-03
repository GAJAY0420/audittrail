"""tiger_audit_trail reusable application."""

from importlib import metadata

try:
    __version__ = metadata.version("tiger_audit_trail")
except metadata.PackageNotFoundError:  # pragma: no cover
    __version__ = "0.1.0"

default_app_config = "audit_trail.apps.AuditTrailConfig"

__all__ = ["__version__", "default_app_config"]
