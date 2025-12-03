"""UI views for handling authentication and the audit timeline."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.generic import TemplateView

from audit_trail import __version__ as AUDITTRAIL_VERSION
from audit_trail.history.service import HistoryEvent, HistoryQueryError, fetch_history
from audit_trail.storage.outbox.models import AuditEventOutbox
from audit_trail.ui.forms import HistorySearchForm


def _format_diff_value(value: Any) -> str:
    if value in (None, "", [], {}):
        return "—"
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if value.get("repr"):
            return str(value["repr"])
        parts = [f"{key}={_format_diff_value(val)}" for key, val in value.items()]
        return ", ".join(parts)
    if isinstance(value, list):
        parts = [_format_diff_value(item) for item in value]
        return ", ".join(parts)
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _build_diff_items(diff_map: Dict[str, Any]) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    for field, change in diff_map.items():
        relation = change.get("relation") if isinstance(change, dict) else None
        if relation == "many_to_many":
            before = _format_diff_value(change.get("removed", []))
            after = _format_diff_value(change.get("added", []))
        elif isinstance(change, dict):
            before = _format_diff_value(change.get("before"))
            after = _format_diff_value(change.get("after"))
        else:
            before = None
            after = _format_diff_value(change)
        items.append(
            {
                "field": field,
                "before": _format_diff_value(before),
                "after": _format_diff_value(after),
                "field_type": change.get("field_type")
                if isinstance(change, dict)
                else "",
            }
        )
    return items


def _format_actor_label(actor_value: Any) -> str:
    if isinstance(actor_value, dict):
        for key in ("username", "name", "email", "id"):
            candidate = actor_value.get(key)
            if candidate:
                return str(candidate)
        return json.dumps(actor_value, ensure_ascii=False)
    if actor_value:
        return str(actor_value)
    return "System"


def _resolve_timestamp(entry: AuditEventOutbox, payload: Dict[str, Any]):
    timestamp = payload.get("timestamp")
    parsed = None
    if isinstance(timestamp, str):
        parsed = parse_datetime(timestamp)
    elif isinstance(timestamp, datetime):
        parsed = timestamp
    if parsed:
        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
        return parsed
    return entry.created_at


def build_timeline_events(limit: int = 25) -> List[Dict[str, Any]]:
    # entries = AuditEventOutbox.objects.filter(status="sent").order_by("-created_at")[
    #     :limit
    # ]
    entries = AuditEventOutbox.objects.all().order_by("-created_at")[:limit]
    events: List[Dict[str, Any]] = []
    for entry in entries:
        payload = (entry.payload or {}).copy()
        context = payload.get("context") or entry.context or {}
        event_type = payload.get("event_type") or context.get("event_type") or "updated"
        timestamp = timezone.localtime(_resolve_timestamp(entry, payload))
        actor_payload = payload.get("actor") or context.get("actor")
        diff_map = payload.get("changes") or payload.get("diff") or {}
        events.append(
            {
                "id": entry.id,
                "model": payload.get("model") or entry.model_label,
                "object_id": payload.get("object_id") or entry.object_pk,
                "summary": payload.get("summary")
                or context.get("summary")
                or f"{event_type.title()} {entry.model_label}",
                "actor": _format_actor_label(actor_payload),
                "actor_details": actor_payload,
                "event_type": event_type,
                "timestamp": timestamp,
                "timestamp_human": naturaltime(timestamp),
                "diff_items": _build_diff_items(diff_map),
                "context": context,
            }
        )
    return events


def _build_history_cards(history_events: List["HistoryEvent"]) -> List[Dict[str, Any]]:
    cards: List[Dict[str, Any]] = []
    for event in history_events:
        parsed = parse_datetime(event.timestamp)
        if parsed and timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
        human = naturaltime(parsed) if parsed else event.timestamp
        diff_items = _build_diff_items(event.diff)
        cards.append(
            {
                "event_id": event.event_id,
                "model": event.model,
                "object_id": event.object_id,
                "summary": event.summary,
                "actor": _format_actor_label(event.actor),
                "actor_details": event.actor,
                "event_type": event.event_type,
                "timestamp": event.timestamp,
                "timestamp_human": human,
                "diff_items": diff_items,
            }
        )
    return cards


class AuditLoginView(LoginView):
    """Render the custom login page with product branding."""

    template_name = "audit_trail/login.html"
    redirect_authenticated_user = True
    success_url = reverse_lazy("audit-trail-timeline")

    def get_context_data(self, **kwargs):  # noqa: ANN001
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "version": AUDITTRAIL_VERSION,
                "hero_title": "Welcome to Audit Trail",
                "tagline": "Enterprise-grade auditing made effortless.",
            }
        )
        return context

    def form_valid(self, form):  # noqa: ANN001
        response = super().form_valid(form)
        if self.request.headers.get("HX-Request"):
            response["HX-Redirect"] = self.get_success_url()
        return response

    def get_form(self, form_class=None):  # noqa: ANN001
        form = super().get_form(form_class)
        for field in form.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"input-control {existing}".strip()
        return form


class AuditTimelineView(LoginRequiredMixin, TemplateView):
    """Secure timeline view that renders the HTMX-powered history page."""

    template_name = "audit_trail/history.html"
    login_url = reverse_lazy("audit-login")

    def get_context_data(self, **kwargs):  # noqa: ANN001
        context = super().get_context_data(**kwargs)
        context["version"] = AUDITTRAIL_VERSION
        context["events"] = build_timeline_events()
        context["feed_url"] = reverse_lazy("audit-timeline-feed")
        return context


class TimelineFeedView(LoginRequiredMixin, TemplateView):
    """HTMX endpoint that renders the timeline feed cards."""

    template_name = "audit_trail/components/timeline_feed.html"
    login_url = reverse_lazy("audit-login")

    def get_limit(self) -> int:
        try:
            return max(1, min(100, int(self.request.GET.get("limit", 25))))
        except (TypeError, ValueError):
            return 25

    def get_context_data(self, **kwargs):  # noqa: ANN001
        context = super().get_context_data(**kwargs)
        context["events"] = build_timeline_events(limit=self.get_limit())
        return context


class HistorySearchView(LoginRequiredMixin, TemplateView):
    """Allow operators to query history from the configured storage backend."""

    template_name = "audit_trail/history_search.html"
    login_url = reverse_lazy("audit-login")

    def get(self, request, *args, **kwargs):  # noqa: ANN001
        form = HistorySearchForm(request.GET or None)
        cards: List[Dict[str, Any]] = []
        next_cursor: str | None = None
        error_message: str | None = None
        if form.is_valid():
            try:
                result = fetch_history(
                    model=form.cleaned_data.get("model"),
                    object_id=form.cleaned_data.get("object_id"),
                    user_id=form.cleaned_data.get("user_id"),
                    limit=form.get_limit(),
                    cursor=form.cleaned_data.get("cursor"),
                )
                cards = _build_history_cards(result.events)
                next_cursor = result.next_cursor
            except HistoryQueryError as exc:  # pragma: no cover - defensive
                form.add_error(None, str(exc))
        elif request.GET:
            error_message = "Please correct the errors below and try again."

        context = self.get_context_data(
            form=form,
            cards=cards,
            next_cursor=next_cursor,
            error_message=error_message,
        )
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):  # noqa: ANN001
        context = super().get_context_data(**kwargs)
        context.setdefault("form", HistorySearchForm())
        context.setdefault("cards", [])
        context.setdefault("next_cursor", None)
        context.setdefault("error_message", None)
        context["version"] = AUDITTRAIL_VERSION
        context["feed_url"] = reverse_lazy("audit-history-search")
        return context
