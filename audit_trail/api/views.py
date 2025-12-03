from __future__ import annotations

from typing import Dict

from rest_framework import response, viewsets

from audit_trail.storage.outbox.models import AuditEventOutbox

from .pagination import TimelinePagination
from .permissions import CanViewAuditLog
from .serializers import AuditEventSerializer


class AuditEventViewSet(viewsets.ViewSet):
    permission_classes = (CanViewAuditLog,)
    pagination_class = TimelinePagination

    def list(self, request):  # noqa: ANN001
        queryset = AuditEventOutbox.objects.filter(status="sent").order_by(
            "-created_at"
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(list(queryset), request)
        serializer = AuditEventSerializer(self._serialize_entries(page), many=True)
        return paginator.get_paginated_response(serializer.data)

    def retrieve(self, request, pk=None):  # noqa: ANN001
        entry = AuditEventOutbox.objects.get(pk=pk, status="sent")
        serializer = AuditEventSerializer(self._serialize_entry(entry))
        return response.Response(serializer.data)

    def _serialize_entries(self, entries):
        return [self._serialize_entry(entry) for entry in entries]

    def _serialize_entry(self, entry) -> Dict[str, str]:
        payload = entry.payload.copy()
        payload.setdefault("id", entry.id)
        return payload
