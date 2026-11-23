"""Offer list filtering, search and stable ordering."""

from django.db.models import Q
from rest_framework import serializers

from core.filters import PositiveIdField, query_values


class OfferQuerySerializer(serializers.Serializer):
    """Validate the documented offer query parameters."""

    creator_id = PositiveIdField()
    min_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, required=False
    )
    max_delivery_time = serializers.IntegerField(min_value=1, required=False)
    ordering = serializers.ChoiceField(
        choices=["updated_at", "-updated_at", "min_price", "-min_price"], required=False
    )
    search = serializers.CharField(required=False)
    page_size = serializers.IntegerField(min_value=1, max_value=100, required=False)


def filter_offers(queryset, request):
    """Apply validated aggregate filters, then search and stable ordering."""
    values = query_values(OfferQuerySerializer, request)
    mapping = {
        "creator_id": "user_id",
        "min_price": "min_price__gte",
        "max_delivery_time": "min_delivery_time__lte",
    }
    criteria = {lookup: values[key] for key, lookup in mapping.items() if key in values}
    queryset = queryset.filter(**criteria)
    return search_offers(queryset, values).order_by(
        values.get("ordering", "-updated_at"), "id"
    )


def search_offers(queryset, values):
    """Search title and description with a case-insensitive substring."""
    if "search" not in values:
        return queryset
    term = values["search"]
    return queryset.filter(Q(title__icontains=term) | Q(description__icontains=term))
