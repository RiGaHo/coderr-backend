"""Profile object permissions."""

from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsProfileOwnerOrReadOnly(BasePermission):
    """Allow authenticated reads and owner-only modifications."""

    def has_object_permission(self, request, view, obj):
        """Compare account identity rather than profile row identity."""
        return request.method in SAFE_METHODS or obj.user_id == request.user.pk
