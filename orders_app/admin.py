"""Inspect orders while preserving purchased service snapshots."""

from django.contrib import admin

from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Read-only snapshot fields with editable order status."""

    list_display = ["id", "title", "customer_user", "business_user", "status"]
    list_filter = ["status"]
    search_fields = ["title", "customer_user__username", "business_user__username"]
    readonly_fields = [
        field.name for field in Order._meta.fields if field.name != "status"
    ]

    def has_add_permission(self, request):
        """Require order creation through the validated API."""
        return False
