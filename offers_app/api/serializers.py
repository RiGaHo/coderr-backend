"""Offer representations and nested tier validation."""

from rest_framework import serializers

from core.validation import StrictFieldsMixin, validate_image
from offers_app.models import Offer, OfferDetail
from offers_app.services import create_offer, update_offer


class DetailSerializer(serializers.ModelSerializer):
    """Represent a complete service tier; IDs are never writable."""

    revisions = serializers.IntegerField(min_value=-1)
    delivery_time_in_days = serializers.IntegerField(min_value=1)
    price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    features = serializers.ListField(
        child=serializers.CharField(max_length=255), allow_empty=False, max_length=100
    )

    class Meta:
        model = OfferDetail
        fields = [
            "id",
            "title",
            "revisions",
            "delivery_time_in_days",
            "price",
            "features",
            "offer_type",
        ]
        read_only_fields = ["id"]
        validators = []

    def to_internal_value(self, data):
        """Allow echoed IDs from the original frontend but never assign them."""
        if isinstance(data, dict) and set(data) - set(self.fields):
            raise serializers.ValidationError("Unknown detail fields.")
        return super().to_internal_value(data)


class DetailReferenceSerializer(serializers.ModelSerializer):
    """Link an offer tier to its authenticated detail endpoint."""

    url = serializers.HyperlinkedIdentityField(view_name="offerdetail")

    class Meta:
        model = OfferDetail
        fields = ["id", "url"]


class UserSummarySerializer(serializers.Serializer):
    """Public offer-owner identity."""

    first_name = serializers.CharField()
    last_name = serializers.CharField()
    username = serializers.CharField()


class OfferReadSerializer(serializers.ModelSerializer):
    """List and detail representation with aggregate tier metadata."""

    details = DetailReferenceSerializer(many=True, read_only=True)
    min_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    min_delivery_time = serializers.IntegerField(read_only=True)
    user_details = UserSummarySerializer(source="user", read_only=True)

    class Meta:
        model = Offer
        fields = [
            "id",
            "user",
            "title",
            "image",
            "description",
            "created_at",
            "updated_at",
            "details",
            "min_price",
            "min_delivery_time",
            "user_details",
        ]


class OfferWriteSerializer(StrictFieldsMixin, serializers.ModelSerializer):
    """Validate nested changes before making any database mutation."""

    details = serializers.JSONField()

    class Meta:
        model = Offer
        fields = ["id", "title", "image", "description", "details"]
        read_only_fields = ["id"]

    def validate_image(self, value):
        """Validate uploaded offer images."""
        return validate_image(value)

    def validate_details(self, value):
        """Require unique tier identities and complete tiers at creation."""
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError("Provide a nonempty list of details.")
        if any(not isinstance(item, dict) for item in value):
            raise serializers.ValidationError("Each detail must be an object.")
        self.validate_tier_types([item.get("offer_type") for item in value])
        return self.validate_tiers(value)

    def validate_tier_types(self, types):
        """Validate scalar tier names before uniqueness checks."""
        allowed = {"basic", "standard", "premium"}
        for tier in types:
            if not isinstance(tier, str) or tier not in allowed:
                raise serializers.ValidationError(
                    "Each detail needs a valid offer_type."
                )
        if len(set(types)) != len(types) or (not self.instance and len(types) != 3):
            raise serializers.ValidationError(
                "Provide each required tier exactly once."
            )

    def validate_tiers(self, value):
        """Validate complete new tiers or partial existing tiers."""
        serializer = DetailSerializer(
            data=value, many=True, partial=bool(self.instance)
        )
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    def create(self, validated_data):
        """Create the offer with its authenticated owner."""
        return create_offer(self.context["request"].user, validated_data)

    def update(self, instance, validated_data):
        """Apply only supplied fields and preserve tier IDs."""
        return update_offer(instance, validated_data)

    def to_representation(self, instance):
        """Return complete tier data after writes."""
        result = {
            name: self.fields[name].to_representation(getattr(instance, name))
            if getattr(instance, name) is not None
            else None
            for name in ["id", "title", "image", "description"]
        }
        result["details"] = DetailSerializer(instance.details.all(), many=True).data
        return result
