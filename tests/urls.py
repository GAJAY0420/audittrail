from django.urls import include, path
from rest_framework.routers import DefaultRouter

from audit_trail.api.views import AuditEventViewSet

router = DefaultRouter()
router.register("audit-events", AuditEventViewSet, basename="audit-events")

urlpatterns = [
    path("", include(router.urls)),
]
