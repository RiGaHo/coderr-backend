"""Shared test fixtures for API contracts and permission boundaries."""

from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from users_app.models import User


def account(name, role="customer"):
    """Create a fixture account with an explicit role."""
    user = User.objects.create_user(
        username=name, email=f"{name}@example.invalid", password="FixturePassword42!"
    )
    user.profile.type = role
    user.profile.save()
    return user


def offer_payload():
    """Return three complete, distinct service tiers."""
    return {
        "title": "Website design",
        "description": "Accessible websites",
        "image": None,
        "details": [
            tier(name, index)
            for index, name in enumerate(["basic", "standard", "premium"], 1)
        ],
    }


def tier(name, index):
    """Return a complete tier suitable for JSON requests."""
    return {
        "title": name,
        "revisions": index,
        "delivery_time_in_days": index * 2,
        "price": index * 100,
        "features": ["Design", "Documentation"],
        "offer_type": name,
    }


class APISetup(APITestCase):
    """Set up participants and an authenticated API client."""

    def setUp(self):
        """Provide two customers and two businesses for ownership tests."""
        self.customer = account("customer")
        self.other_customer = account("other_customer")
        self.business = account("business", "business")
        self.other_business = account("other_business", "business")

    def login_as(self, user):
        """Use real token authentication rather than force_authenticate."""
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def make_offer(self):
        """Create a service offering through the public API contract."""
        self.login_as(self.business)
        response = self.client.post("/api/offers/", offer_payload())
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def make_order(self):
        """Purchase the basic service tier as a customer."""
        offer = self.make_offer()
        self.login_as(self.customer)
        response = self.client.post(
            "/api/orders/", {"offer_detail_id": offer["details"][0]["id"]}
        )
        self.assertEqual(response.status_code, 201, response.data)
        return offer, response.data

    def make_review(self):
        """Create one customer review through the API."""
        self.login_as(self.customer)
        response = self.client.post("/api/reviews/", self.review_payload())
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def review_payload(self):
        """Return a valid review request."""
        return {
            "business_user": self.business.pk,
            "rating": 4,
            "description": "Good service",
        }

    def assert_keys(self, data, expected):
        """Assert required JSON properties are present."""
        self.assertTrue(set(expected) <= set(data), data)
