"""Review query parameters and stable ordering."""

from rest_framework import serializers

from core.filters import PositiveIdField, query_values


class ReviewQuerySerializer(serializers.Serializer):
    """Validate business and reviewer filters and allowed ordering fields."""

    business_user_id = PositiveIdField()
    reviewer_id = PositiveIdField()
    ordering = serializers.ChoiceField(
        choices=["updated_at", "-updated_at", "rating", "-rating"], required=False
    )


def filter_reviews(queryset, request):
    """Apply explicit review filters with stable tie-breaking."""
    values = query_values(ReviewQuerySerializer, request)
    ordering = values.pop("ordering", "-updated_at")
    return queryset.filter(**values).order_by(ordering, "id")
