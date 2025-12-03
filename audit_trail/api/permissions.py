from rest_framework.permissions import BasePermission


class CanViewAuditLog(BasePermission):
    def has_permission(self, request, view):  # noqa: ANN001
        return (
            request.user.has_perm("audit_trail.view_audit_log")
            if request.user and request.user.is_authenticated
            else False
        )
