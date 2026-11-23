"""Authentication and profile contract tests."""

from django.contrib.auth import get_user_model

from .base import APISetup


class AccountTests(APISetup):
    """Validate registration, authentication and protected profile fields."""

    def registration_payload(self):
        """Return fresh valid registration data."""
        return {
            "username": "newuser",
            "email": "new@example.invalid",
            "password": "NewPassword42!",
            "repeated_password": "NewPassword42!",
            "type": "customer",
        }

    def test_registration_response_and_hash(self):
        """Registration returns exact contract keys and hashes passwords."""
        response = self.client.post("/api/registration/", self.registration_payload())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(set(response.data), {"token", "username", "email", "user_id"})
        user = get_user_model().objects.get(pk=response.data["user_id"])
        self.assertTrue(user.check_password("NewPassword42!"))
        self.assertNotEqual(user.password, "NewPassword42!")
        self.assertEqual(user.profile.type, "customer")
        self.assertIsInstance(response.data["token"], str)

    def test_registration_invalid_variants(self):
        """Reject invalid role, confirmation, email and privileged inputs."""
        for changes in [
            {"type": "admin"},
            {"repeated_password": "no"},
            {"email": "bad"},
            {"is_staff": True},
        ]:
            with self.subTest(changes=changes):
                data = self.registration_payload() | changes
                self.assertEqual(
                    self.client.post("/api/registration/", data).status_code, 400
                )
        self.assertFalse(get_user_model().objects.filter(username="newuser").exists())

    def test_registration_required_fields(self):
        """Each documented registration field is required."""
        for field in self.registration_payload():
            data = self.registration_payload()
            del data[field]
            with self.subTest(field=field):
                self.assertEqual(
                    self.client.post("/api/registration/", data).status_code, 400
                )

    def test_duplicate_identity(self):
        """Reject both duplicate username and case-insensitive duplicate email."""
        for change in [
            {"username": self.customer.username},
            {"email": self.customer.email.upper()},
        ]:
            self.assertEqual(
                self.client.post(
                    "/api/registration/", self.registration_payload() | change
                ).status_code,
                400,
            )

    def test_login_response_and_failure(self):
        """Login returns the same identity and rejects bad credentials with 400."""
        data = {"username": self.customer.username, "password": "FixturePassword42!"}
        response = self.client.post("/api/login/", data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user_id"], self.customer.pk)
        self.assertEqual(set(response.data), {"token", "username", "email", "user_id"})
        data["password"] = "wrong"
        self.assertEqual(self.client.post("/api/login/", data).status_code, 400)

    def test_inactive_login(self):
        """Inactive accounts cannot obtain a token."""
        self.customer.is_active = False
        self.customer.save()
        response = self.client.post(
            "/api/login/", {"username": "customer", "password": "FixturePassword42!"}
        )
        self.assertEqual(response.status_code, 400)

    def test_anonymous_and_invalid_token(self):
        """Protected profile resources return 401 with a Token challenge."""
        for token in [None, "Token invalid"]:
            self.client.credentials(**({"HTTP_AUTHORIZATION": token} if token else {}))
            for path in [
                f"/api/profile/{self.customer.pk}/",
                "/api/profiles/business/",
                "/api/profiles/customer/",
            ]:
                response = self.client.get(path)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response["WWW-Authenticate"], "Token")

    def test_profile_contract_and_lists(self):
        """Profiles contain identities and empty strings for unset fields."""
        self.login_as(self.customer)
        response = self.client.get(f"/api/profile/{self.business.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assert_keys(
            response.data, ["user", "username", "email", "type", "file", "created_at"]
        )
        fields = "first_name last_name location tel description working_hours".split()
        for field in fields:
            self.assertEqual(response.data[field], "")

    def test_profile_directories(self):
        """Directories are unpaginated and contain only the requested role."""
        self.login_as(self.customer)
        for role in ["business", "customer"]:
            data = self.client.get(f"/api/profiles/{role}/").data
            self.assertIsInstance(data, list)
            self.assertEqual(len(data), 2)
            self.assertTrue(all(item["type"] == role for item in data))

    def test_profile_partial_update(self):
        """PATCH changes account fields and profile fields together."""
        self.login_as(self.customer)
        changes = {
            "first_name": "Ada",
            "location": "Berlin",
            "email": "changed@example.invalid",
        }
        response = self.client.patch(f"/api/profile/{self.customer.pk}/", changes)
        self.assertEqual(response.status_code, 200, response.data)
        for key, value in changes.items():
            self.assertEqual(response.data[key], value)
        self.assertEqual(response.data["last_name"], "")

    def test_profile_owner_and_immutable_fields(self):
        """Reject foreign-profile writes."""
        self.login_as(self.customer)
        path = f"/api/profile/{self.business.pk}/"
        self.assertEqual(self.client.patch(path, {"location": "x"}).status_code, 403)

    def test_profile_protected_fields(self):
        """Reject role, identity and privilege changes."""
        self.login_as(self.customer)
        path = f"/api/profile/{self.customer.pk}/"
        changes = {
            "type": "business",
            "user": self.business.pk,
            "username": "stolen",
            "is_staff": True,
        }
        for key, value in changes.items():
            self.assertEqual(self.client.patch(path, {key: value}).status_code, 400)
        self.assert_customer_role_unchanged()

    def assert_customer_role_unchanged(self):
        """Reload the account to verify rejected privilege changes."""
        self.customer.refresh_from_db()
        self.assertFalse(self.customer.is_staff)
        self.assertEqual(self.customer.profile.type, "customer")

    def test_profile_missing_and_email_collision(self):
        """Return 404 for missing users and keep data unchanged on collisions."""
        self.login_as(self.customer)
        self.assertEqual(self.client.get("/api/profile/99999/").status_code, 404)
        response = self.client.patch(
            f"/api/profile/{self.customer.pk}/",
            {"email": self.business.email, "first_name": "bad"},
        )
        self.assertEqual(response.status_code, 400)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.first_name, "")
