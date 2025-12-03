"""Helpers for masking and unmasking sensitive audit values."""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, Literal

from django.core.exceptions import ImproperlyConfigured

from audit_trail.utils.crypto import decrypt_sensitive, encrypt_sensitive

MASK_PREFIX = "masked:"
LOGGER = logging.getLogger(__name__)


def mask_value(value: Any) -> tuple[str, str | None]:
    normalized = "" if value is None else str(value)
    digest = _digest(normalized)
    ciphertext: str | None = None
    try:
        ciphertext = encrypt_sensitive(normalized)
    except ImproperlyConfigured:
        LOGGER.warning(
            "AUDITTRAIL_SENSITIVE_KEY is not configured; storing masked diff only."
        )
    return f"{MASK_PREFIX}{digest}", ciphertext


def unmask_change(
    change: Dict[str, Any], *, position: Literal["before", "after"] = "after"
) -> str:
    key = f"encrypted_{position}"
    token = change.get(key)
    if not token:
        raise ValueError(f"Change payload does not include {key}.")
    return decrypt_sensitive(token)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
