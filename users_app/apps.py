"""Account application configuration."""

from django.apps import AppConfig


class UsersConfig(AppConfig):
    """Register automatic profile creation."""

    name = "users_app"

    def ready(self):
        """Connect profile lifecycle handlers."""
        from . import signals  # noqa: F401
