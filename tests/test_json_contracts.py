"""Verify rendered JSON types independently of serializer Python values."""

from .base import APISetup

TIER_SCHEMA = {
    "id": int,
    "title": str,
    "revisions": int,
    "delivery_time_in_days": int,
    "price": (int, float),
    "features": list,
    "offer_type": str,
}
OFFER_SCHEMA = {
    "id": int,
    "user": int,
    "title": str,
    "description": str,
    "details": list,
    "min_price": (int, float),
    "min_delivery_time": int,
}
TIMESTAMPS = {"created_at": str, "updated_at": str}


class JSONContractTests(APISetup):
    """Check actual JSON payloads, including numeric prices and null images."""

    def assert_schema(self, data, schema):
        """Require each field and its documented JSON-compatible type."""
        self.assert_keys(data, schema)
        for field, expected_type in schema.items():
            self.assertIsInstance(data[field], expected_type, (field, data[field]))

    def test_offer_json_types(self):
        """The offer collection has pagination and typed nested references."""
        self.make_offer()
        data = self.client.get("/api/offers/").json()
        self.assert_schema(data, {"count": int, "results": list})
        self.assertIsNone(data["next"])
        row = data["results"][0]
        self.assert_schema(row, OFFER_SCHEMA | TIMESTAMPS)
        self.assert_schema(row["details"][0], {"id": int, "url": str})
        self.assert_schema(
            row["user_details"], {"username": str, "first_name": str, "last_name": str}
        )
        self.assertIsNone(row["image"])

    def test_tier_json_types(self):
        """Prices serialize as JSON numbers, not strings or Decimal objects."""
        offer = self.make_offer()
        pk = offer["details"][0]["id"]
        data = self.client.get(f"/api/offerdetails/{pk}/").json()
        self.assert_schema(data, TIER_SCHEMA)
        self.assertTrue(all(isinstance(feature, str) for feature in data["features"]))

    def test_order_json_types(self):
        """Order snapshots expose both account identities and timestamps."""
        self.make_order()
        data = self.client.get("/api/orders/").json()[0]
        schema = {"customer_user": int, "business_user": int, "status": str}
        self.assert_schema(data, TIER_SCHEMA | TIMESTAMPS | schema)

    def test_review_json_types(self):
        """Reviews expose numeric account IDs and ratings with textual content."""
        self.make_review()
        data = self.client.get("/api/reviews/").json()[0]
        schema = {
            "id": int,
            "business_user": int,
            "reviewer": int,
            "rating": int,
            "description": str,
        }
        self.assert_schema(data, schema | TIMESTAMPS)

    def test_profile_json_types(self):
        """The profile identity and all required text fields have stable types."""
        self.login_as(self.customer)
        data = self.client.get(f"/api/profile/{self.customer.pk}/").json()
        fields = (
            "username first_name last_name location tel description "
            "working_hours type email created_at"
        ).split()
        self.assert_schema(data, dict.fromkeys(fields, str) | {"user": int})
        self.assertIsNone(data["file"])
        self.assertIsNone(data["uploaded_at"])
