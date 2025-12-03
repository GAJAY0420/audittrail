"""Utilities for encrypting and decrypting sensitive audit payloads."""

from __future__ import annotations

import base64
import hashlib
from functools import lru_cache
from typing import Final

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

_SENSITIVE_PREFIX: Final[str] = "enc:"


def _derive_key(raw_key: str) -> bytes:
    digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


@lru_cache()
def _get_cipher() -> Fernet:
    raw_key = getattr(settings, "AUDITTRAIL_SENSITIVE_KEY", None)
    if not raw_key:
        raise ImproperlyConfigured(
            "AUDITTRAIL_SENSITIVE_KEY must be set to encrypt sensitive fields."
        )
    try:
        if len(raw_key) == 44:
            base64.urlsafe_b64decode(raw_key.encode("utf-8"))
            encoded = raw_key.encode("utf-8")
        else:
            raise ValueError
    except Exception:
        encoded = _derive_key(raw_key)
    return Fernet(encoded)


def encrypt_sensitive(value: str) -> str:
    token = _get_cipher().encrypt(value.encode("utf-8"))
    return f"{_SENSITIVE_PREFIX}{token.decode('utf-8')}"


def decrypt_sensitive(value: str) -> str:
    if not value.startswith(_SENSITIVE_PREFIX):
        raise ValueError("Value is not encrypted with the audit trail cipher.")
    token = value[len(_SENSITIVE_PREFIX) :].encode("utf-8")
    try:
        return _get_cipher().decrypt(token).decode("utf-8")
    except InvalidToken as exc:  # pragma: no cover - indicates tampering
        raise ValueError("Unable to decrypt sensitive value.") from exc


def is_encrypted_value(value: str | None) -> bool:
    return bool(value and value.startswith(_SENSITIVE_PREFIX))
