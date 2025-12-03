from rest_framework.routers import DefaultRouter

from .views import AuditEventViewSet


def build_router(prefix: str = "audit-events") -> DefaultRouter:
    router = DefaultRouter()
    router.register(prefix, AuditEventViewSet, basename="audit-events")
    return router
