"""Fast password hashing only for isolated automated tests."""

from core.settings import *  # noqa: F403

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
