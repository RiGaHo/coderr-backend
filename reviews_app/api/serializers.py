"""Validate review targets, rating values and ownership-safe edits."""

from rest_framework import serializers

from core.validation import StrictFieldsMixin
from reviews_app.models import Review
from users_app.models import User


class ReviewSerializer(StrictFieldsMixin, serializers.ModelSerializer):
    """Represent reviews and validate customer submissions."""

    business_user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(profile__type="business")
    )
    rating = serializers.IntegerField(min_value=1, max_value=5)

    class Meta:
        model = Review
        fields = [
            "id",
            "business_user",
            "reviewer",
            "rating",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "reviewer", "created_at", "updated_at"]
        validators = []

    def validate(self, attrs):
        """Catch duplicate reviews before the database uniqueness constraint."""
        if (
            not self.instance
            and Review.objects.filter(
                business_user=attrs["business_user"],
                reviewer=self.context["request"].user,
            ).exists()
        ):
            raise serializers.ValidationError(
                "You have already reviewed this business."
            )
        return attrs


class ReviewUpdateSerializer(ReviewSerializer):
    """Restrict review edits to rating and description."""

    business_user = serializers.PrimaryKeyRelatedField(read_only=True)
