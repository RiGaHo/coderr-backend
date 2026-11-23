"""Explicitly opt in to the original frontend's local guest accounts."""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from users_app.models import User

DEMO_ACCOUNTS = [("andrey", "asdasd", "customer"), ("kevin", "asdasd24", "business")]


class Command(BaseCommand):
    """Create known demo accounts without changing existing identities."""

    help = "Create local-only guest accounts; never use on a public instance."

    def add_arguments(self, parser):
        """Require explicit acknowledgement of intentionally weak demo credentials."""
        parser.add_argument("--allow-insecure-demo", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        """Reject production use and collisions before creating either account."""
        if not settings.DEBUG or not options["allow_insecure_demo"]:
            raise CommandError("Requires DEBUG=true and --allow-insecure-demo.")
        names = [name for name, _, _ in DEMO_ACCOUNTS]
        if User.objects.filter(username__in=names).exists():
            raise CommandError("Demo usernames exist; no accounts changed.")
        for name, password, role in DEMO_ACCOUNTS:
            create_demo(name, password, role)
        self.stdout.write(self.style.SUCCESS("Local demo accounts created."))


def create_demo(name, password, role):
    """Use password hashing and assign the expected frontend role."""
    user = User.objects.create_user(name, f"{name}@example.invalid", password)
    user.profile.type = role
    user.profile.save(update_fields=["type"])
