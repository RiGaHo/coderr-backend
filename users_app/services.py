"""Atomic account and profile mutations."""

from django.db import transaction
from django.utils import timezone
from rest_framework.authtoken.models import Token

from .models import User


@transaction.atomic
def register_user(data):
    """Create a hashed-password account and assign its validated role."""
    role = data.pop("type")
    data.pop("repeated_password")
    user = User.objects.create_user(**data)
    user.profile.type = role
    user.profile.save(update_fields=["type"])
    return user


def auth_response(user):
    """Return the documented authentication payload."""
    token, _ = Token.objects.get_or_create(user=user)
    return {
        "token": token.key,
        "username": user.username,
        "email": user.email,
        "user_id": user.pk,
    }


@transaction.atomic
def update_profile(profile, data):
    """Save account and profile fields together."""
    account = data.pop("user", {})
    for key, value in account.items():
        setattr(profile.user, key, value)
    profile.user.save()
    if "file" in data:
        profile.uploaded_at = timezone.now()
    for key, value in data.items():
        setattr(profile, key, value)
    profile.save()
    return profile
