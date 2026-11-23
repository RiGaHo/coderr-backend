"""Review authorship and customer role checks."""

from rest_framework.permissions import BasePermission


class ReviewPermission(BasePermission):
    """Only customers create reviews; only authors mutate them."""

    def has_permission(self, request, view):
        """Check the creator role after authentication."""
        return view.action != "create" or request.user.profile.type == "customer"

    def has_object_permission(self, request, view, obj):
        """Compare the authenticated account with the immutable author."""
        return obj.reviewer_id == request.user.pk
