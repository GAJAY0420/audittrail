from __future__ import annotations

from typing import Any, Dict

from django.apps import apps
from django.conf import settings
from django.core.exceptions import FieldDoesNotExist
from django.db import models, transaction
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_save
from django.dispatch import receiver

from audit_trail.middleware import get_current_user, get_request_meta
from audit_trail.registry.registry import registry
from audit_trail.storage.outbox.models import AuditEventOutbox
from audit_trail.tasks import trigger_outbox_dispatch
from audit_trail.utils.actor import format_actor_payload, resolve_actor_from_settings
from audit_trail.utils.sensitive import mask_value

from .m2m_tracker import tracker
from ..utils.services import build_event
from .validators import validate_diff

_snapshots: Dict[str, Dict[str, Any]] = {}


def _model_label(model: Any) -> str:
    if not model:
        return "Unknown"
    meta = getattr(model, "_meta", None)
    if meta and hasattr(meta, "label"):
        return meta.label
    return getattr(model, "__name__", str(model))


def _get_model_field(instance, field_name: str):
    try:
        return instance._meta.get_field(field_name)  # type: ignore[attr-defined]
    except FieldDoesNotExist:
        return None


def _describe_related_instance(obj: models.Model | None) -> Dict[str, Any] | None:
    if obj is None:
        return None
    return {
        "pk": getattr(obj, "pk", None),
        "repr": str(obj),
        "model": _model_label(obj.__class__),
    }


def _serialize_related_value(field, value):
    if value is None:
        return None
    if isinstance(value, models.Model):
        return _describe_related_instance(value)
    rel_model = getattr(getattr(field, "remote_field", None), "model", None)
    if rel_model is None:
        return value
    try:
        target = rel_model.objects.get(pk=value)
        return _describe_related_instance(target)
    except rel_model.DoesNotExist:  # type: ignore[attr-defined]
        return {
            "pk": value,
            "repr": str(value),
            "model": _model_label(rel_model),
        }


def _serialize_value(field, value):
    if field and field.is_relation and not field.many_to_many:  # type: ignore[attr-defined]
        return _serialize_related_value(field, value)
    return value


def _relation_type(field) -> str:
    if not field:
        return "field"
    if getattr(field, "many_to_many", False):
        return "many_to_many"
    if getattr(field, "one_to_one", False):
        return "one_to_one"
    if getattr(field, "many_to_one", False):
        return "foreign_key"
    if getattr(field, "one_to_many", False):
        return "reverse_relation"
    return "field"


def _serialize_scalar_change(
    field_name: str,
    field,
    old_value: Any,
    new_value: Any,
    *,
    encrypted_before: str | None = None,
    encrypted_after: str | None = None,
) -> Dict[str, Any]:
    field_type = getattr(field, "get_internal_type", lambda: "Field")()
    label_source = getattr(field, "verbose_name", None) if field else None
    label = label_source or field_name
    change = {
        "field": field_name,
        "label": str(label),
        "field_type": field_type,
        "relation": _relation_type(field),
        "before": _serialize_value(field, old_value),
        "after": _serialize_value(field, new_value),
    }
    if encrypted_before:
        change["encrypted_before"] = encrypted_before
    if encrypted_after:
        change["encrypted_after"] = encrypted_after
    return change


def _describe_related_collection(model, pk_values):
    if not model or not pk_values:
        return []
    identifiers = list(pk_values)
    if not identifiers:
        return []
    queryset = model.objects.filter(pk__in=identifiers)
    resolved = {obj.pk: obj for obj in queryset}
    results = []
    for pk in sorted(identifiers):
        obj = resolved.get(pk)
        if obj:
            results.append(_describe_related_instance(obj))
        else:
            results.append({"pk": pk, "repr": str(pk), "model": _model_label(model)})
    return results


def _serialize_m2m_change(
    field_name: str, field, payload: Dict[str, Any]
) -> Dict[str, Any]:
    model = payload.get("model")
    if isinstance(model, str):
        try:
            model = apps.get_model(model)
        except LookupError:  # pragma: no cover - defensive
            model = None
    added = _describe_related_collection(model, payload.get("add", set()))
    removed = _describe_related_collection(model, payload.get("remove", set()))
    field_type = getattr(field, "get_internal_type", lambda: "ManyToManyField")()
    label_source = payload.get("label") if isinstance(payload, dict) else None
    if not label_source and field:
        label_source = getattr(field, "verbose_name", None)
    label = label_source or field_name
    return {
        "field": field_name,
        "label": str(label),
        "field_type": field_type,
        "relation": "many_to_many",
        "model": _model_label(model),
        "added": added,
        "removed": removed,
    }


def _mixin_active(instance) -> bool:
    return bool(getattr(instance, "_audit_trail_mixin_active", False))


def _object_key(instance) -> str:
    """
    Generate a unique key for an object instance.

    Args:
        instance: The model instance.

    Returns:
        str: A unique key string in the format 'app_label.model_name:pk'.
    """
    return f"{instance._meta.label}:{instance.pk}"  # type: ignore[attr-defined]


def _tracked_field_names(config) -> tuple[str, ...]:
    """Return the ordered list of fields, including sensitive-only entries."""

    ordered: list[str] = []
    for field in list(getattr(config, "fields", ())) + list(
        getattr(config, "sensitive", ())
    ):
        if field not in ordered:
            ordered.append(field)
    return tuple(ordered)


def _capture_snapshot(instance) -> None:
    """
    Capture the state of an object before changes are saved.

    Stores the snapshot in a module-level dictionary keyed by the object's unique key.
    Only captures fields registered in the audit configuration.

    Args:
        instance: The model instance being saved.
    """
    if instance._state.adding or not instance.pk:  # type: ignore[attr-defined]
        return
    config = registry.get(instance._meta.label)
    if not config:
        return
    try:
        previous = instance.__class__.objects.get(pk=instance.pk)
    except instance.__class__.DoesNotExist:  # type: ignore[attr-defined]
        return
    tracked_fields = _tracked_field_names(config)
    if not tracked_fields:
        return
    data: Dict[str, Any] = {}
    for field in tracked_fields:
        try:
            data[field] = getattr(previous, field)
        except AttributeError:
            continue
    _snapshots[_object_key(instance)] = data


def _diff(instance, created: bool) -> Dict[str, Dict[str, Any]]:
    config = registry.get(instance._meta.label)
    if not config:
        return {}
    before_state = _snapshots.pop(_object_key(instance), {})
    diff: Dict[str, Dict[str, Any]] = {}
    for field_name in _tracked_field_names(config):
        if not hasattr(instance, field_name):
            continue
        model_field = _get_model_field(instance, field_name)
        new_value = getattr(instance, field_name)
        old_value = before_state.get(field_name) if not created else None
        if new_value == old_value:
            continue
        encrypted_before: str | None = None
        encrypted_after: str | None = None
        if field_name in config.sensitive:
            if new_value is not None:
                new_value, encrypted_after = mask_value(new_value)
            if old_value is not None:
                old_value, encrypted_before = mask_value(old_value)
        diff[field_name] = _serialize_scalar_change(
            field_name,
            model_field,
            old_value,
            new_value,
            encrypted_before=encrypted_before,
            encrypted_after=encrypted_after,
        )
    m2m_data = tracker.consume(_object_key(instance))
    for field_name, payload in m2m_data.items():
        model_field = _get_model_field(instance, field_name)
        diff[field_name] = _serialize_m2m_change(field_name, model_field, payload)
    return diff


def _emit_m2m_event(instance, field_name: str) -> None:
    """Push a standalone audit event for the provided M2M field if needed."""

    payload = tracker.consume_field(_object_key(instance), field_name)
    if not payload:
        return
    additions = payload.get("add") or set()
    removals = payload.get("remove") or set()
    if not additions and not removals:
        return
    model_field = _get_model_field(instance, field_name)
    diff = {field_name: _serialize_m2m_change(field_name, model_field, payload)}
    _enqueue(instance, diff, event_type="updated")


def _build_context(instance) -> Dict[str, Any]:
    context: Dict[str, Any] = {}
    if hasattr(instance, "get_audit_context"):
        context = instance.get_audit_context() or {}

    actor_payload = context.get("actor")
    formatted_actor = format_actor_payload(actor_payload) if actor_payload else None
    if formatted_actor:
        context["actor"] = formatted_actor
    elif "actor" in context:
        context.pop("actor")

    if not context.get("actor"):
        resolved_actor = resolve_actor_from_settings()
        if resolved_actor:
            context["actor"] = resolved_actor
    if not context.get("actor"):
        middleware_user = get_current_user()
        if middleware_user:
            fallback_actor = format_actor_payload(middleware_user)
            if fallback_actor:
                context["actor"] = fallback_actor

    request_meta = get_request_meta({}) or {}
    if request_meta:
        request_context = context.setdefault("request", {})
        for key in ("ip", "user_agent", "method", "path", "user"):
            value = request_meta.get(key)
            if value and key not in request_context:
                request_context[key] = value
    return context


def _jsonable(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, set):
        return [_jsonable(item) for item in sorted(value)]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    return str(value)


def _enqueue(instance, diff: Dict[str, Dict[str, Any]], *, event_type: str) -> None:
    validated = validate_diff({k: _jsonable(v) for k, v in diff.items()})
    context = _build_context(instance)
    payload = build_event(instance, validated, context=context)
    payload["event_type"] = event_type
    AuditEventOutbox.objects.enqueue(
        instance=instance, payload=payload, context=context
    )
    if not getattr(settings, "AUDITTRAIL_USE_CELERY", True):
        transaction.on_commit(lambda: trigger_outbox_dispatch())


def record_pre_save(instance) -> None:
    if registry.get(instance._meta.label):
        _capture_snapshot(instance)


def record_post_save(instance, *, created: bool) -> None:
    if not registry.get(instance._meta.label):
        return
    diff = _diff(instance, created)
    if not diff:
        return
    _enqueue(instance, diff, event_type="created" if created else "updated")


def record_post_delete(instance) -> None:
    config = registry.get(instance._meta.label)
    if not config:
        return
    diff = {}
    for field_name in _tracked_field_names(config):
        if not hasattr(instance, field_name):
            continue
        model_field = _get_model_field(instance, field_name)
        old_value = getattr(instance, field_name)
        encrypted_before: str | None = None
        if field_name in config.sensitive and old_value is not None:
            old_value, encrypted_before = mask_value(old_value)
        diff[field_name] = _serialize_scalar_change(
            field_name,
            model_field,
            old_value,
            None,
            encrypted_before=encrypted_before,
        )
    _enqueue(instance, diff, event_type="deleted")


def _resolve_m2m_field(instance, sender) -> str | None:
    for field in instance._meta.many_to_many:  # type: ignore[attr-defined]
        if field.remote_field.through == sender:  # type: ignore[attr-defined]
            return field.name
    return None


@receiver(pre_save)
def audittrail_pre_save(sender, instance, **kwargs):  # noqa: ANN001
    if _mixin_active(instance):
        return
    record_pre_save(instance)


@receiver(post_save)
def audittrail_post_save(sender, instance, created, **kwargs):  # noqa: ANN001
    if _mixin_active(instance):
        return
    record_post_save(instance, created=created)


@receiver(post_delete)
def audittrail_post_delete(sender, instance, **kwargs):  # noqa: ANN001
    if _mixin_active(instance):
        return
    record_post_delete(instance)


@receiver(m2m_changed)
def audittrail_m2m(sender, instance, action, reverse, model, pk_set, **kwargs):  # noqa: ANN001
    config = registry.get(instance._meta.label)
    if not config:
        return
    if action not in {"post_add", "post_remove"}:
        return
    field_name = _resolve_m2m_field(instance, sender)
    if not field_name or field_name not in config.m2m:
        return
    model_field = _get_model_field(instance, field_name)
    label_source = getattr(model_field, "verbose_name", None) if model_field else None
    tracker.track(
        obj_key=_object_key(instance),
        field_name=field_name,
        action=action,
        pk_set=pk_set,
        model=model,
        label=label_source or field_name,
    )
    _emit_m2m_event(instance, field_name)
