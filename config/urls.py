"""URL configuration for the standalone audit trail service."""

from __future__ import annotations

from django.contrib import admin
from django.urls import include, path

from audit_trail.api.routers import build_router
from audit_trail.ui.views import (
    AuditLoginView,
    AuditTimelineView,
    HistorySearchView,
    TimelineFeedView,
)

router = build_router()

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("", AuditLoginView.as_view(), name="audit-login"),
    path("timeline/", AuditTimelineView.as_view(), name="audit-trail-timeline"),
    path("timeline/feed/", TimelineFeedView.as_view(), name="audit-timeline-feed"),
    path("history/search/", HistorySearchView.as_view(), name="audit-history-search"),
]
