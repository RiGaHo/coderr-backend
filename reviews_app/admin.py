"""Review inspection and moderation."""

from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """Review moderation without changing its author or business target."""

    list_display = ["id", "business_user", "reviewer", "rating", "updated_at"]
    list_filter = ["rating"]
    search_fields = ["description", "reviewer__username"]
    readonly_fields = ["business_user", "reviewer", "created_at", "updated_at"]

    def has_add_permission(self, request):
        """Require creation through the customer-validated API."""
        return False
