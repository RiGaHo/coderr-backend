"""Historical order snapshots independent of mutable offer details."""

from django.conf import settings
from django.db import models

from offers_app.models import OFFER_TYPES


class Order(models.Model):
    """Purchased service data retained even after the original offer is deleted."""

    STATUSES = [
        ("in_progress", "In progress"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]
    customer_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="customer_orders",
    )
    business_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="business_orders",
    )
    title = models.CharField(max_length=255)
    revisions = models.IntegerField()
    delivery_time_in_days = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    features = models.JSONField()
    offer_type = models.CharField(max_length=8, choices=OFFER_TYPES)
    status = models.CharField(max_length=11, choices=STATUSES, default="in_progress")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    status__in=["in_progress", "completed", "cancelled"]
                ),
                name="valid_order_status",
            )
        ]

    def __str__(self):
        """Identify the order and its purchased service."""
        return f"Order {self.pk}: {self.title}"
