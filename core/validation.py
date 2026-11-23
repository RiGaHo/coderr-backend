"""Shared input validation used by resource serializers."""

from collections.abc import Mapping

from rest_framework import serializers


class StrictFieldsMixin:
    """Reject unknown fields and explicit writes to protected attributes."""

    def to_internal_value(self, data):
        """Reject unsupported keys before normal serializer validation."""
        if not isinstance(data, Mapping):
            return super().to_internal_value(data)
        allowed = {name for name, field in self.fields.items() if not field.read_only}
        extra = set(data) - allowed
        if extra:
            raise serializers.ValidationError(
                {key: "Field is not writable." for key in extra}
            )
        return super().to_internal_value(data)


def validate_image(value):
    """Restrict image uploads by decoded format, size and pixel dimensions."""
    if value is None:
        return value
    if value.size > 5 * 1024 * 1024:
        raise serializers.ValidationError("Images must not exceed 5 MiB.")
    image = value.image
    if image.format not in {"JPEG", "PNG", "WEBP"}:
        raise serializers.ValidationError("Use JPEG, PNG or WebP images.")
    if image.width * image.height > 20_000_000:
        raise serializers.ValidationError("Images must not exceed 20 megapixels.")
    return value
