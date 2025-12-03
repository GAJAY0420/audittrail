"""Custom middleware utilities for the audit trail package."""

from __future__ import annotations

import threading
from typing import Any, Callable, Dict, Optional

from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, HttpResponse
from rest_framework.permissions import BasePermission

_thread_state = threading.local()


def set_current_user(user: Any | None) -> None:
    """Persist the current user for retrieval outside the request cycle."""

    setattr(_thread_state, "current_user", user)


def get_current_user(default: Any | None = None) -> Any | None:
    """Return the current user stored by the middleware or ``default``."""

    return getattr(_thread_state, "current_user", default)


def set_request_meta(meta: Optional[Dict[str, Any]]) -> None:
    """Persist lightweight request metadata (IP, UA, path) for audit usage."""

    setattr(_thread_state, "request_meta", meta)


def get_request_meta(
    default: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Return stored request metadata or ``default`` when unavailable."""

    return getattr(_thread_state, "request_meta", default)


def _is_superuser(request: HttpRequest) -> bool:
    """Return True when the request is associated with an active superuser."""

    user = getattr(request, "user", None)
    return bool(user and user.is_active and user.is_superuser)


def _client_ip(request: HttpRequest) -> Optional[str]:
    """Resolve the best-effort client IP from headers or the socket."""

    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _serialize_request_user(user: Any | None) -> Optional[str]:
    """Return a display label for the authenticated user if possible."""

    if not user:
        return None
    if hasattr(user, "get_username"):
        username = user.get_username()
        if username:
            return str(username)
    if hasattr(user, "username"):
        username = getattr(user, "username")
        if username:
            return str(username)
    return str(user)


def _build_request_meta(request: HttpRequest, user: Any | None) -> Dict[str, Any]:
    """Collect sanitized request metadata for audit context enrichment."""

    meta: Dict[str, Any] = {}
    ip = _client_ip(request)
    if ip:
        meta["ip"] = ip
    user_agent = request.META.get("HTTP_USER_AGENT")
    if user_agent:
        meta["user_agent"] = user_agent
    path_getter = getattr(request, "get_full_path", None)
    if callable(path_getter):
        path = path_getter()
    else:
        path = getattr(request, "path", None)
    if path:
        meta["path"] = path
    method = getattr(request, "method", None)
    if method:
        meta["method"] = method
    label = _serialize_request_user(user)
    if label:
        meta["user"] = label
    return meta


class CustomPermissionMiddleware:
    """Patch DRF BasePermission to automatically allow superusers."""

    _patched = False

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response
        self._ensure_patch()

    def __call__(self, request: HttpRequest) -> HttpResponse:
        try:
            user = getattr(request, "user", None)
            stored_user = user if user and not isinstance(user, AnonymousUser) else None
            set_current_user(stored_user)
            set_request_meta(_build_request_meta(request, stored_user))
            return self.get_response(request)
        finally:
            set_current_user(None)
            set_request_meta(None)

    def _ensure_patch(self) -> None:
        if self.__class__._patched:
            return

        original_has_permission = BasePermission.has_permission
        original_has_object_permission = BasePermission.has_object_permission

        def _has_permission(  # type: ignore[override]
            self: BasePermission, request: HttpRequest, view: Any
        ) -> bool:
            if _is_superuser(request):
                return True
            return original_has_permission(self, request, view)

        def _has_object_permission(  # type: ignore[override]
            self: BasePermission,
            request: HttpRequest,
            view: Any,
            obj: Any,
        ) -> bool:
            if _is_superuser(request):
                return True
            return original_has_object_permission(self, request, view, obj)

        BasePermission.has_permission = _has_permission  # type: ignore[assignment]
        BasePermission.has_object_permission = _has_object_permission  # type: ignore[assignment]
        self.__class__._patched = True
