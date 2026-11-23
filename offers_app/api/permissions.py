"""Business role and offer ownership permissions."""

from rest_framework.permissions import SAFE_METHODS, BasePermission


class OfferPermission(BasePermission):
    """Public listing, authenticated details and owner-only mutations."""

    def has_permission(self, request, view):
        """Restrict creation to business accounts."""
        if view.action == "list":
            return True
        if not request.user.is_authenticated:
            return False
        return view.action != "create" or request.user.profile.type == "business"

    def has_object_permission(self, request, view, obj):
        """Restrict writes to the offer owner."""
        return request.method in SAFE_METHODS or obj.user_id == request.user.pk
