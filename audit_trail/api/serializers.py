from __future__ import annotations

from rest_framework import serializers


class AuditEventSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    model = serializers.CharField()
    object_id = serializers.CharField()
    timestamp = serializers.DateTimeField()
    summary = serializers.CharField()
    actor = serializers.CharField(allow_null=True)
    diff = serializers.JSONField()
    context = serializers.JSONField()
