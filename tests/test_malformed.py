"""Malformed JSON structures must never turn input errors into server errors."""

from .base import APISetup, offer_payload


class MalformedInputTests(APISetup):
    """Exercise unexpected root and nested JSON types."""

    def test_nonobject_registration_and_login(self):
        """Authentication schemas require JSON objects."""
        for endpoint in ["registration/", "login/"]:
            for data in [[{}], "text", 42, None]:
                response = self.client.generic(
                    "POST",
                    f"/api/{endpoint}",
                    self.encode(data),
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 400)

    def encode(self, data):
        """Encode null and scalar request bodies without APIClient defaults."""
        import json

        return json.dumps(data)

    def test_nonobject_resource_requests(self):
        """Resource writes reject nonobject JSON with a client error."""
        self.login_as(self.business)
        for data in [[{}], "text", 42, None]:
            response = self.client.generic(
                "POST",
                "/api/offers/",
                self.encode(data),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 400)

    def test_nonscalar_tier_identity(self):
        """Malformed tier identifiers cannot trigger unhashable-key errors."""
        self.login_as(self.business)
        for value in [[], {}, 42, None]:
            data = offer_payload()
            data["details"][0]["offer_type"] = value
            self.assertEqual(self.client.post("/api/offers/", data).status_code, 400)
