"""URL routes for the audit trail UI surfaces."""

from django.urls import path

from audit_trail.ui.views import HistorySearchView, TimelineFeedView

app_name = "audit_trail"

urlpatterns = [
    path(
        "timeline/feed/",
        TimelineFeedView.as_view(),
        name="audit-timeline-feed",
    ),
    path(
        "history/search/",
        HistorySearchView.as_view(),
        name="audit-history-search",
    ),
]
