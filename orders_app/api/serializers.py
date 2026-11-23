"""Immutable order snapshots and narrow write contracts."""

from rest_framework import serializers

from core.validation import StrictFieldsMixin
from orders_app.models import Order
from orders_app.services import create_order


class OrderSerializer(serializers.ModelSerializer):
    """Represent all documented purchased service properties."""

    class Meta:
        model = Order
        fields = [
            "id",
            "customer_user",
            "business_user",
            "title",
            "revisions",
            "delivery_time_in_days",
            "price",
            "features",
            "offer_type",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class OrderCreateSerializer(StrictFieldsMixin, serializers.ModelSerializer):
    """Accept only a positive tier ID; parties are assigned server-side."""

    offer_detail_id = serializers.IntegerField(min_value=1, write_only=True)

    class Meta:
        model = Order
        fields = ["offer_detail_id"]

    def create(self, validated_data):
        """Build a persistent snapshot of the selected service tier."""
        return create_order(
            self.context["request"].user, validated_data["offer_detail_id"]
        )

    def to_representation(self, instance):
        """Return the full order after creation."""
        return OrderSerializer(instance, context=self.context).data


class OrderUpdateSerializer(StrictFieldsMixin, serializers.ModelSerializer):
    """Allow only status changes."""

    class Meta:
        model = Order
        fields = ["status"]

    def to_representation(self, instance):
        """Return the full order after a status change."""
        return OrderSerializer(instance, context=self.context).data
