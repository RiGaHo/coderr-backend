"""Customer reviews of business profiles."""

from django.conf import settings
from django.db import models


class Review(models.Model):
    """One review per customer and business account."""

    business_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_reviews",
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="written_reviews",
    )
    rating = models.PositiveSmallIntegerField()
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["business_user", "reviewer"], name="unique_review"
            ),
            models.CheckConstraint(
                condition=models.Q(rating__gte=1, rating__lte=5), name="valid_rating"
            ),
        ]

    def __str__(self):
        """Identify the review in administration."""
        return f"Review {self.pk}: {self.rating}/5"
