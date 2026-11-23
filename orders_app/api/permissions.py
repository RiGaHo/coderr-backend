"""Customer creation and business-owner update permissions."""

from rest_framework.permissions import BasePermission


class OrderPermission(BasePermission):
    """Enforce role restrictions in addition to authenticated access."""

    def has_permission(self, request, view):
        """Only customers can create orders."""
        return view.action != "create" or request.user.profile.type == "customer"

    def has_object_permission(self, request, view, obj):
        """Only the assigned business account can update the status."""
        return (
            obj.business_user_id == request.user.pk
            and request.user.profile.type == "business"
        )
