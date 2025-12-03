"""Fixtures for exercising the actor resolver."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class DummyUser:
    """Simple stand-in object that mimics Django's User behavior."""

    username: str
    email: Optional[str] = None
    pk: Optional[int] = None

    def get_username(self) -> str:
        """Return the username just like Django's AbstractUser."""

        return self.username


def return_username() -> str:
    """Return a string identifier to mimic middleware helpers."""

    return "middleware-user"


def return_user_object() -> DummyUser:
    """Return a user-like object so the resolver exercises attribute access."""

    return DummyUser(username="resolver-user", email="user@example.com", pk=7)
