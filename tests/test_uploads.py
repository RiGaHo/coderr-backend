"""Actual image decoding, multipart writes and media responses."""

import json
from io import BytesIO
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image

from .base import APISetup, offer_payload


def picture(name="image.png", image_format="PNG"):
    """Build a small real image, not a file with an image-like extension."""
    buffer = BytesIO()
    Image.new("RGB", (3, 3), "blue").save(buffer, format=image_format)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class UploadTests(APISetup):
    """Test upload handling without leaving test media on disk."""

    def setUp(self):
        """Isolate uploaded media for every test."""
        super().setUp()
        directory = TemporaryDirectory(prefix="coderr-media-")
        self.addCleanup(directory.cleanup)
        settings = override_settings(MEDIA_ROOT=directory.name)
        settings.enable()
        self.addCleanup(settings.disable)

    def test_profile_image_upload(self):
        """Accept multipart profile images and provide a resolvable media URL."""
        self.login_as(self.customer)
        path = f"/api/profile/{self.customer.pk}/"
        response = self.client.patch(path, {"file": picture()}, format="multipart")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("/media/profiles/", response.data["file"])
        self.assertIsNotNone(response.data["uploaded_at"])
        self.customer.profile.refresh_from_db()
        self.assertTrue(
            self.customer.profile.file.storage.exists(self.customer.profile.file.name)
        )

    def test_invalid_profile_image(self):
        """Reject non-images even if filename and MIME pretend to be PNG."""
        self.login_as(self.customer)
        fake = SimpleUploadedFile(
            "bad.png", b"not a real image", content_type="image/png"
        )
        path = f"/api/profile/{self.customer.pk}/"
        self.assertEqual(
            self.client.patch(path, {"file": fake}, format="multipart").status_code, 400
        )

    def test_disallowed_format(self):
        """Reject decoded GIF files outside the documented accepted formats."""
        self.login_as(self.customer)
        data = {"file": picture("image.gif", "GIF")}
        response = self.client.patch(
            f"/api/profile/{self.customer.pk}/", data, format="multipart"
        )
        self.assertEqual(response.status_code, 400)

    def test_oversized_image(self):
        """Reject a decodable image whose uploaded size exceeds five MiB."""
        self.login_as(self.customer)
        data = picture().read() + b"x" * (5 * 1024 * 1024)
        upload = SimpleUploadedFile("large.png", data, content_type="image/png")
        response = self.client.patch(
            f"/api/profile/{self.customer.pk}/", {"file": upload}, format="multipart"
        )
        self.assertEqual(response.status_code, 400)

    def test_offer_image_patch(self):
        """Support the frontend's create-then-upload request sequence."""
        offer = self.make_offer()
        response = self.client.patch(
            f"/api/offers/{offer['id']}/", {"image": picture()}, format="multipart"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("/media/offers/", response.data["image"])
        self.assertEqual(response.data["details"], offer["details"])

    def test_offer_multipart_creation(self):
        """Support a complete multipart offer with JSON-encoded tiers."""
        self.login_as(self.business)
        data = offer_payload()
        data["details"] = json.dumps(data["details"])
        data["image"] = picture()
        response = self.client.post("/api/offers/", data, format="multipart")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(len(response.data["details"]), 3)

    def test_offer_bad_multipart_json(self):
        """Malformed nested JSON produces 400 without saving an offer."""
        self.login_as(self.business)
        response = self.client.post(
            "/api/offers/",
            {"title": "Bad", "description": "Bad", "details": "["},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)
