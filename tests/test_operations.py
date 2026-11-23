"""Administration, deployment configuration and opt-in demo safety."""

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from users_app.models import User

from .base import APISetup


class OperationsTests(APISetup):
    """Check operational safeguards that are not ordinary API CRUD."""

    def test_demo_requires_explicit_opt_in(self):
        """Do not create weak guest accounts without explicit acknowledgement."""
        with override_settings(DEBUG=True), self.assertRaises(CommandError):
            call_command("seed_demo", stdout=StringIO())
        self.assertFalse(User.objects.filter(username="andrey").exists())

    def test_demo_rejects_production(self):
        """Even an explicit flag cannot create demo accounts with DEBUG=false."""
        with override_settings(DEBUG=False), self.assertRaises(CommandError):
            call_command("seed_demo", allow_insecure_demo=True, stdout=StringIO())
        self.assertFalse(User.objects.filter(username="andrey").exists())

    @override_settings(DEBUG=True)
    def test_demo_credentials_and_existing_accounts(self):
        """Create compatible guest accounts once without resetting identities."""
        call_command("seed_demo", allow_insecure_demo=True, stdout=StringIO())
        for name, password, role in [
            ("andrey", "asdasd", "customer"),
            ("kevin", "asdasd24", "business"),
        ]:
            user = User.objects.get(username=name)
            self.assertTrue(user.check_password(password))
            self.assertEqual(user.profile.type, role)
        with self.assertRaises(CommandError):
            call_command("seed_demo", allow_insecure_demo=True, stdout=StringIO())

    @override_settings(DEBUG=True)
    def test_demo_transaction_rollback(self):
        """A failure creating either account rolls back the whole seed operation."""
        target = "users_app.management.commands.seed_demo.create_demo"
        with patch(target, side_effect=RuntimeError), self.assertRaises(RuntimeError):
            call_command("seed_demo", allow_insecure_demo=True, stdout=StringIO())
        self.assertFalse(User.objects.filter(username="andrey").exists())

    def test_admin_pages(self):
        """Registered models are accessible to a real staff superuser."""
        admin = User.objects.create_superuser(
            "admin", "admin@example.invalid", "AdminPassword42!"
        )
        self.client.force_login(admin)
        for path in [
            "users_app/user",
            "users_app/userprofile",
            "offers_app/offer",
            "orders_app/order",
            "reviews_app/review",
        ]:
            self.assertEqual(self.client.get(f"/admin/{path}/").status_code, 200)

    def test_cors_development_origin(self):
        """Allow the documented local frontend origin, never arbitrary origins."""
        response = self.client.get(
            "/api/base-info/", HTTP_ORIGIN="http://127.0.0.1:5500"
        )
        self.assertEqual(
            response["Access-Control-Allow-Origin"], "http://127.0.0.1:5500"
        )
        response = self.client.get(
            "/api/base-info/", HTTP_ORIGIN="https://untrusted.invalid"
        )
        self.assertNotIn("Access-Control-Allow-Origin", response)
