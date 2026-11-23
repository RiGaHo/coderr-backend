"""Offers and their three service tiers."""

from django.conf import settings
from django.db import models

OFFER_TYPES = [("basic", "Basic"), ("standard", "Standard"), ("premium", "Premium")]


class Offer(models.Model):
    """A business user's service offering."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="offers"
    )
    title = models.CharField(max_length=255)
    image = models.ImageField(upload_to="offers/", blank=True, null=True)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]

    def __str__(self):
        """Display the offer title in administration."""
        return self.title


class OfferDetail(models.Model):
    """One uniquely named tier within an offer."""

    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name="details")
    title = models.CharField(max_length=255)
    revisions = models.IntegerField()
    delivery_time_in_days = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    features = models.JSONField()
    offer_type = models.CharField(max_length=8, choices=OFFER_TYPES)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["offer", "offer_type"], name="unique_tier"),
            models.CheckConstraint(
                condition=models.Q(revisions__gte=-1), name="valid_revisions"
            ),
            models.CheckConstraint(
                condition=models.Q(price__gte=0), name="valid_price"
            ),
            models.CheckConstraint(
                condition=models.Q(delivery_time_in_days__gte=1), name="valid_delivery"
            ),
            models.CheckConstraint(
                condition=models.Q(offer_type__in=["basic", "standard", "premium"]),
                name="valid_tier",
            ),
        ]

    def __str__(self):
        """Display the tier title in administration."""
        return f"{self.title} ({self.offer_type})"
