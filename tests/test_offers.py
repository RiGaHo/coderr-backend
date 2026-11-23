"""Offer contract, tier identity and filter tests."""

from unittest.mock import patch

from offers_app.models import Offer, OfferDetail
from offers_app.services import create_offer, update_offer

from .base import APISetup, offer_payload


class OfferTests(APISetup):
    """Exercise documented read/write schemas and business permissions."""

    def test_public_list_and_private_detail(self):
        """Only collection reads are public."""
        offer = self.make_offer()
        self.client.credentials()
        response = self.client.get("/api/offers/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data), {"count", "next", "previous", "results"})
        paths = [
            f"/api/offers/{offer['id']}/",
            f"/api/offerdetails/{offer['details'][0]['id']}/",
        ]
        for path in paths:
            self.assertEqual(self.client.get(path).status_code, 401)
        self.assert_anonymous_offer_creation()

    def test_create_read_contracts(self):
        """Mutations embed complete tiers and reads provide aggregate metadata."""
        offer = self.make_offer()
        self.assertEqual(set(offer), {"id", "title", "image", "description", "details"})
        self.assertEqual(len(offer["details"]), 3)
        response = self.client.get(f"/api/offers/{offer['id']}/")
        fields = ["user", "created_at", "updated_at", "min_price", "min_delivery_time"]
        self.assert_keys(response.data, fields)
        self.assertEqual(response.data["min_price"], 100)
        self.assertEqual(response.data["min_delivery_time"], 2)

    def test_detail_references_resolve(self):
        """Every detail reference resolves to the complete purchased tier."""
        offer = self.make_offer()
        data = self.client.get(f"/api/offers/{offer['id']}/").data
        for reference, expected in zip(data["details"], offer["details"], strict=True):
            self.assertEqual(set(reference), {"id", "url"})
            detail = self.client.get(reference["url"])
            self.assertEqual(detail.status_code, 200)
            self.assertEqual(detail.data, expected)

    def test_required_three_tiers(self):
        """Reject incomplete and duplicate tier sets without creating rows."""
        self.login_as(self.business)
        data = offer_payload()
        for details in [[], data["details"][:2], [data["details"][0]] * 3, None, {}]:
            response = self.client.post("/api/offers/", data | {"details": details})
            self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(Offer.objects.count(), 0)
        self.assertEqual(OfferDetail.objects.count(), 0)

    def test_invalid_tier_values(self):
        """Reject malformed service values."""
        self.login_as(self.business)
        changes = [
            {"price": -1},
            {"revisions": -2},
            {"delivery_time_in_days": 0},
            {"features": []},
            {"title": ""},
        ]
        for change in changes:
            data = offer_payload()
            data["details"][0].update(change)
            self.assertEqual(self.client.post("/api/offers/", data).status_code, 400)

    def test_missing_tier_fields(self):
        """Every documented tier property is required on creation."""
        self.login_as(self.business)
        for field in offer_payload()["details"][0]:
            data = offer_payload()
            del data["details"][0][field]
            self.assertEqual(self.client.post("/api/offers/", data).status_code, 400)

    def test_partial_tier_ids_and_unlimited_revisions(self):
        """PATCH preserves other fields and ignores echoed detail IDs."""
        offer = self.make_offer()
        changes = {"details": [{"id": 99999, "offer_type": "basic", "revisions": -1}]}
        response = self.client.patch(f"/api/offers/{offer['id']}/", changes)
        self.assertEqual(response.status_code, 200, response.data)
        expected = offer["details"]
        expected[0]["revisions"] = -1
        self.assertEqual(response.data["details"], expected)
        self.assertEqual(response.data["title"], offer["title"])

    def test_invalid_patch_is_atomic(self):
        """A bad second tier prevents changes to the title and first tier."""
        offer = self.make_offer()
        details = [
            {"offer_type": "basic", "price": 5},
            {"offer_type": "premium", "price": -1},
        ]
        changes = {"title": "No", "details": details}
        response = self.client.patch(f"/api/offers/{offer['id']}/", changes)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Offer.objects.get(pk=offer["id"]).title, offer["title"])
        detail = OfferDetail.objects.get(pk=offer["details"][0]["id"])
        self.assertEqual(detail.price, 100)

    def test_service_create_transaction_rollback(self):
        """A database write failure rolls back the parent offer as well."""
        with patch(
            "offers_app.services.OfferDetail.objects.create", side_effect=RuntimeError
        ):
            with self.assertRaises(RuntimeError):
                create_offer(self.business, offer_payload())
        self.assertEqual(Offer.objects.count(), 0)

    def test_service_update_transaction_rollback(self):
        """A nested write failure rolls back a parent field change."""
        offer = self.make_offer()
        instance = Offer.objects.get(pk=offer["id"])
        with patch("django.db.models.query.QuerySet.update", side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):
                update_offer(
                    instance,
                    {"title": "No", "details": [{"offer_type": "basic", "price": 5}]},
                )
        instance.refresh_from_db()
        self.assertEqual(instance.title, offer["title"])

    def test_role_and_owner_permissions(self):
        """Customers cannot create and foreign accounts cannot mutate offers."""
        offer = self.make_offer()
        path = f"/api/offers/{offer['id']}/"
        for user in [self.customer, self.other_business]:
            self.login_as(user)
            self.assertEqual(self.client.patch(path, {"title": "No"}).status_code, 403)
            self.assertEqual(self.client.delete(path).status_code, 403)
        self.login_as(self.customer)
        response = self.client.post("/api/offers/", offer_payload())
        self.assertEqual(response.status_code, 403)

    def test_filters_and_search(self):
        """Validate creator, aggregate bounds, search and empty controls."""
        self.make_offer()
        for query, count in [
            ("creator_id=99999", 0),
            ("min_price=101", 0),
            ("max_delivery_time=1", 0),
            ("search=web", 1),
            ("search=missing", 0),
            ("creator_id=&ordering=", 1),
        ]:
            response = self.client.get(f"/api/offers/?{query}")
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data["count"], count)

    def test_invalid_filters(self):
        """Malformed filter parameters return 400 instead of server errors."""
        for query in [
            "creator_id=x",
            "min_price=NaN",
            "max_delivery_time=-1",
            "ordering=title",
            "page_size=0",
            "page_size=101",
        ]:
            self.assertEqual(self.client.get(f"/api/offers/?{query}").status_code, 400)

    def test_pagination(self):
        """Default six-item pages expose correct next/previous links."""
        for _ in range(7):
            create_offer(self.business, offer_payload())
        response = self.client.get("/api/offers/")
        self.assertEqual(response.data["count"], 7)
        self.assertEqual(len(response.data["results"]), 6)
        self.assertIsNone(response.data["previous"])
        page = self.client.get(response.data["next"])
        self.assertEqual(len(page.data["results"]), 1)
        self.assertIsNotNone(page.data["previous"])
        self.assertEqual(
            len(self.client.get("/api/offers/?page_size=2").data["results"]), 2
        )

    def test_delete_and_missing_ids(self):
        """Owner deletion returns empty 204 and cascades only service tiers."""
        offer = self.make_offer()
        response = self.client.delete(f"/api/offers/{offer['id']}/")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertEqual(OfferDetail.objects.count(), 0)
        self.assertEqual(
            self.client.get(f"/api/offers/{offer['id']}/").status_code, 404
        )
        self.assertEqual(self.client.get("/api/offerdetails/99999/").status_code, 404)

    def assert_anonymous_offer_creation(self):
        """Anonymous users cannot create offers."""
        response = self.client.post("/api/offers/", offer_payload())
        self.assertEqual(response.status_code, 401)

    def test_ordering_by_min_price(self):
        """Ordering uses aggregate minimum prices rather than arbitrary tier rows."""
        low = create_offer(self.business, offer_payload())
        data = offer_payload()
        for detail in data["details"]:
            detail["price"] += 50
        high = create_offer(self.business, data)
        for ordering, expected in [
            ("min_price", [low.pk, high.pk]),
            ("-min_price", [high.pk, low.pk]),
        ]:
            response = self.client.get(f"/api/offers/?ordering={ordering}")
            self.assertEqual([row["id"] for row in response.data["results"]], expected)
