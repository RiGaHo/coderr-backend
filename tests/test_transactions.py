"""Order snapshot, review integrity and platform-statistic tests."""

from django.db import IntegrityError, transaction

from offers_app.models import OfferDetail
from reviews_app.models import Review
from users_app.models import User

from .base import APISetup


class OrderTests(APISetup):
    """Verify immutable purchased data and isolated account access."""

    def test_order_contract(self):
        """Orders copy service data and assign authenticated parties."""
        offer, order = self.make_order()
        fields = "id customer_user business_user status created_at updated_at".split()
        self.assert_keys(order, fields)
        self.assertEqual(order["customer_user"], self.customer.pk)
        self.assertEqual(order["business_user"], self.business.pk)
        self.assertEqual(order["status"], "in_progress")
        self.assert_snapshot(order, offer["details"][0])

    def assert_snapshot(self, actual, expected):
        """Compare every purchased service field."""
        fields = [
            "title",
            "revisions",
            "delivery_time_in_days",
            "price",
            "features",
            "offer_type",
        ]
        for field in fields:
            self.assertEqual(actual[field], expected[field])

    def test_order_snapshot_survives_offer_edit_and_delete(self):
        """Completed order data persists unchanged after source deletion."""
        offer, order = self.make_order()
        self.login_as(self.business)
        path = f"/api/orders/{order['id']}/"
        self.assertEqual(
            self.client.patch(path, {"status": "completed"}).status_code, 200
        )
        self.modify_and_delete_offer(offer)
        stored = self.client.get("/api/orders/").data[0]
        self.assert_snapshot(stored, order)
        self.assertEqual(stored["status"], "completed")

    def modify_and_delete_offer(self, offer):
        """Change a purchased source tier, then delete its entire offer."""
        detail = OfferDetail.objects.get(pk=offer["details"][0]["id"])
        detail.price = 999
        detail.save()
        path = f"/api/offers/{offer['id']}/"
        self.assertEqual(self.client.delete(path).status_code, 204)

    def test_order_lists_are_personal(self):
        """Only the customer and assigned business see each order."""
        _, order = self.make_order()
        path = f"/api/orders/{order['id']}/"
        for user in [self.customer, self.business]:
            self.login_as(user)
            self.assertEqual(self.client.get("/api/orders/").data[0]["id"], order["id"])
        for user in [self.other_customer, self.other_business]:
            self.login_as(user)
            self.assertEqual(self.client.get("/api/orders/").data, [])
            response = self.client.patch(path, {"status": "completed"})
            self.assertEqual(response.status_code, 404)

    def test_order_role_permissions(self):
        """Only customers create orders and their assigned business updates."""
        offer, order = self.make_order()
        path = f"/api/orders/{order['id']}/"
        data = {"status": "completed"}
        self.assertEqual(self.client.patch(path, data).status_code, 403)
        self.login_as(self.business)
        create = {"offer_detail_id": offer["details"][0]["id"]}
        self.assertEqual(self.client.post("/api/orders/", create).status_code, 403)
        response = self.client.patch(path, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "completed")

    def test_invalid_order_inputs(self):
        """Reject malformed IDs, absent tiers and party injection."""
        self.login_as(self.customer)
        for data in [
            {},
            {"offer_detail_id": "x"},
            {"offer_detail_id": -1},
            {"offer_detail_id": 1, "customer_user": 3},
        ]:
            self.assertEqual(self.client.post("/api/orders/", data).status_code, 400)
        self.assertEqual(
            self.client.post("/api/orders/", {"offer_detail_id": 99999}).status_code,
            404,
        )

    def test_order_update_fields(self):
        """Reject invalid statuses and snapshot mutations."""
        _, order = self.make_order()
        self.login_as(self.business)
        path = f"/api/orders/{order['id']}/"
        changes = [
            {"status": "done"},
            {"price": 1},
            {"title": "No"},
            {"customer_user": self.business.pk},
        ]
        for data in changes:
            self.assertEqual(self.client.patch(path, data).status_code, 400)

    def test_missing_order(self):
        """An absent order cannot be updated."""
        self.login_as(self.business)
        response = self.client.patch("/api/orders/99999/", {"status": "completed"})
        self.assertEqual(response.status_code, 404)

    def test_counts_statuses_and_alias(self):
        """Count only the requested status with both completion keys."""
        _, order = self.make_order()
        self.login_as(self.business)
        self.assert_counts(1, 0)
        path = f"/api/orders/{order['id']}/"
        self.client.patch(path, {"status": "completed"})
        self.assert_counts(0, 1)
        self.client.patch(path, {"status": "cancelled"})
        self.assert_counts(0, 0)

    def assert_counts(self, active, completed):
        """Check both exact count response contracts."""
        base = f"/api/order-count/{self.business.pk}/"
        complete = f"/api/completed-order-count/{self.business.pk}/"
        expected = {"order_count": completed, "completed_order_count": completed}
        self.assertEqual(self.client.get(base).data, {"order_count": active})
        self.assertEqual(self.client.get(complete).data, expected)

    def test_count_requires_business(self):
        """Missing and customer identities are not business count targets."""
        self.login_as(self.customer)
        for pk in [self.customer.pk, 99999]:
            for endpoint in ["order-count", "completed-order-count"]:
                self.assertEqual(
                    self.client.get(f"/api/{endpoint}/{pk}/").status_code, 404
                )


class ReviewTests(APISetup):
    """Verify authorship restrictions and duplicate safeguards."""

    def test_review_contract(self):
        """Review creation returns documented identities and timestamps."""
        review = self.make_review()
        fields = "id business_user reviewer rating description created_at updated_at"
        self.assertEqual(set(review), set(fields.split()))
        self.assertEqual(review["reviewer"], self.customer.pk)
        self.assertIsInstance(review["rating"], int)
        self.assertEqual(self.client.get("/api/reviews/").data, [review])

    def test_duplicate_review(self):
        """Duplicate API submissions fail with the chosen 400 response."""
        self.make_review()
        self.assertEqual(
            self.client.post("/api/reviews/", self.review_payload()).status_code, 400
        )
        self.assertEqual(Review.objects.count(), 1)

    def test_database_duplicate_constraint(self):
        """Database uniqueness also prevents bypassing API validation."""
        self.make_review()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Review.objects.create(
                business_user=self.business,
                reviewer=self.customer,
                rating=3,
                description="Duplicate",
            )
        self.assertEqual(Review.objects.count(), 1)

    def test_review_invalid_values_and_targets(self):
        """Only integer ratings 1–5 and real business targets are valid."""
        self.login_as(self.customer)
        for rating in [0, 6, 1.5]:
            self.assert_bad_review({"rating": rating})
        for target in [self.customer.pk, 99999]:
            self.assert_bad_review({"business_user": target})
        self.assert_bad_review({"reviewer": self.other_customer.pk})
        self.assertEqual(Review.objects.count(), 0)

    def assert_bad_review(self, changes):
        """Submit one invalid review variant and check its error status."""
        response = self.client.post("/api/reviews/", self.review_payload() | changes)
        self.assertEqual(response.status_code, 400)

    def test_review_role_and_ownership(self):
        """Businesses cannot create and other users cannot mutate reviews."""
        review = self.make_review()
        path = f"/api/reviews/{review['id']}/"
        for user in [self.business, self.other_customer]:
            self.login_as(user)
            self.assertEqual(self.client.patch(path, {"rating": 5}).status_code, 403)
            self.assertEqual(self.client.delete(path).status_code, 403)
        self.login_as(self.business)
        response = self.client.post("/api/reviews/", self.review_payload())
        self.assertEqual(response.status_code, 403)

    def test_review_patch_and_delete(self):
        """Authors can edit content and receive an empty delete response."""
        review = self.make_review()
        path = f"/api/reviews/{review['id']}/"
        response = self.client.patch(path, {"rating": 5})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["description"], review["description"])
        self.assert_protected_review_fields(path)
        response = self.client.delete(path)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")

    def assert_protected_review_fields(self, path):
        """Reject changes to either party of an existing review."""
        changes = [
            {"business_user": self.other_business.pk},
            {"reviewer": self.other_customer.pk},
        ]
        for data in changes:
            self.assertEqual(self.client.patch(path, data).status_code, 400)

    def test_review_filter_and_ordering(self):
        """Filter by either party and order by the documented rating field."""
        self.make_review()
        self.login_as(self.other_customer)
        self.client.post("/api/reviews/", self.review_payload() | {"rating": 2})
        path = f"/api/reviews/?reviewer_id={self.customer.pk}"
        self.assertEqual(len(self.client.get(path).data), 1)
        path = f"/api/reviews/?business_user_id={self.other_business.pk}"
        self.assertEqual(len(self.client.get(path).data), 0)
        data = self.client.get("/api/reviews/?ordering=rating").data
        self.assertEqual([item["rating"] for item in data], [2, 4])

    def test_review_invalid_filter_and_missing_object(self):
        """Bad filters and absent reviews receive distinct error statuses."""
        self.login_as(self.customer)
        self.assertEqual(
            self.client.get("/api/reviews/?reviewer_id=bad").status_code, 400
        )
        response = self.client.patch("/api/reviews/99999/", {"rating": 4})
        self.assertEqual(response.status_code, 404)


class PlatformTests(APISetup):
    """Public statistics and anonymous endpoint protection."""

    def test_empty_stats(self):
        """Statistics are public and handle a database without reviews/offers."""
        response = self.client.get("/api/base-info/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            {
                "review_count": 0,
                "average_rating": 0.0,
                "business_profile_count": 2,
                "offer_count": 0,
            },
        )

    def test_nonempty_stats(self):
        """Counts reflect stored objects and the mean uses one decimal."""
        self.make_offer()
        self.make_review()
        self.login_as(self.other_customer)
        self.client.post("/api/reviews/", self.review_payload() | {"rating": 5})
        self.client.credentials()
        expected = {
            "review_count": 2,
            "average_rating": 4.5,
            "business_profile_count": 2,
            "offer_count": 1,
        }
        self.assertEqual(self.client.get("/api/base-info/").data, expected)

    def test_anonymous_protected_endpoints(self):
        """No protected order/review route is accidentally public."""
        for path in [
            "orders/",
            "reviews/",
            "order-count/1/",
            "completed-order-count/1/",
        ]:
            self.assertEqual(self.client.get(f"/api/{path}").status_code, 401)
        for path in ["orders/", "reviews/"]:
            self.assertEqual(self.client.post(f"/api/{path}", {}).status_code, 401)

    def test_undocumented_operations(self):
        """Do not expose order deletion, review retrieval or PUT writes."""
        self.login_as(self.business)
        for path in ["offers/1/", "profile/1/", "orders/1/", "reviews/1/"]:
            self.assertEqual(self.client.put(f"/api/{path}", {}).status_code, 405)
        self.assertEqual(self.client.delete("/api/orders/1/").status_code, 405)
        self.assertEqual(self.client.get("/api/reviews/1/").status_code, 405)

    def test_rounding_to_one_decimal(self):
        """Nonterminating means are rounded to one decimal."""
        self.make_review()
        self.login_as(self.other_customer)
        self.client.post("/api/reviews/", self.review_payload() | {"rating": 4})
        self.client.post(
            "/api/reviews/",
            {
                "business_user": self.other_business.pk,
                "rating": 5,
                "description": "Great",
            },
        )
        self.assertEqual(self.client.get("/api/base-info/").data["average_rating"], 4.3)

    def test_completely_empty_database(self):
        """All four statistics are zero before any registration."""
        User.objects.all().delete()
        data = self.client.get("/api/base-info/").data
        self.assertEqual(
            data,
            {
                "review_count": 0,
                "average_rating": 0.0,
                "business_profile_count": 0,
                "offer_count": 0,
            },
        )
