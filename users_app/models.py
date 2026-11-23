"""Accounts and public profile data."""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower


class User(AbstractUser):
    """Account with a database-enforced case-insensitive email identity."""

    email = models.EmailField(unique=True)

    class Meta:
        constraints = [models.UniqueConstraint(Lower("email"), name="unique_email_ci")]


class UserProfile(models.Model):
    """Role and editable profile information associated with an account."""

    TYPES = [("customer", "Customer"), ("business", "Business")]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    type = models.CharField(max_length=8, choices=TYPES, default="customer")
    file = models.ImageField(upload_to="profiles/", blank=True, null=True)
    location = models.CharField(max_length=255, blank=True)
    tel = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    working_hours = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    uploaded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["user_id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(type__in=["customer", "business"]),
                name="valid_profile_type",
            )
        ]

    def __str__(self):
        """Identify the profile in administration."""
        return f"{self.user.username} ({self.type})"
