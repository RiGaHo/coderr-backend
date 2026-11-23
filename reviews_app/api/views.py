"""Authenticated review CRUD and public platform statistics."""

from decimal import ROUND_HALF_UP, Decimal

from django.db import IntegrityError, transaction
from django.db.models import Avg
from rest_framework import mixins, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from offers_app.models import Offer
from reviews_app.models import Review
from users_app.models import UserProfile

from .filters import filter_reviews
from .permissions import ReviewPermission
from .serializers import ReviewSerializer, ReviewUpdateSerializer


class ReviewViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Review listing, creation and author-only mutations."""

    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated, ReviewPermission]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        """Apply query filters only to the collection endpoint."""
        if self.action == "list":
            return filter_reviews(self.queryset, self.request)
        return self.queryset.all()

    def get_serializer_class(self):
        """Reject changes to the reviewed business account."""
        return (
            ReviewUpdateSerializer
            if self.action == "partial_update"
            else ReviewSerializer
        )

    def perform_create(self, serializer):
        """Assign the authenticated author and handle concurrent duplicates."""
        try:
            with transaction.atomic():
                serializer.save(reviewer=self.request.user)
        except IntegrityError as error:
            raise ValidationError("You have already reviewed this business.") from error


class BaseInfoView(APIView):
    """Public aggregate statistics derived from stored data."""

    permission_classes = [AllowAny]

    def get(self, request):
        """Round the mean to one decimal and handle an empty database."""
        average = Review.objects.aggregate(value=Avg("rating"))["value"] or 0
        rounded = Decimal(str(average)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        return Response(
            {
                "review_count": Review.objects.count(),
                "average_rating": float(rounded),
                "business_profile_count": UserProfile.objects.filter(
                    type="business"
                ).count(),
                "offer_count": Offer.objects.count(),
            }
        )
