"""Offer CRUD and authenticated tier lookup."""

from django.db.models import Min
from rest_framework import generics, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated

from offers_app.models import Offer, OfferDetail

from .filters import filter_offers
from .permissions import OfferPermission
from .serializers import DetailSerializer, OfferReadSerializer, OfferWriteSerializer


class OfferPagination(PageNumberPagination):
    """Match the original frontend page size."""

    page_size = 6
    page_size_query_param = "page_size"
    max_page_size = 100


class OfferViewSet(viewsets.ModelViewSet):
    """Expose only the five documented offer operations."""

    queryset = Offer.objects.select_related("user").prefetch_related("details")
    serializer_class = OfferReadSerializer
    permission_classes = [OfferPermission]
    pagination_class = OfferPagination
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        """Annotate tier minima before list filtering."""
        queryset = self.queryset.annotate(
            min_price=Min("details__price"),
            min_delivery_time=Min("details__delivery_time_in_days"),
        )
        return (
            filter_offers(queryset, self.request) if self.action == "list" else queryset
        )

    def get_serializer_class(self):
        """Use the distinct documented read and mutation representations."""
        if self.action in {"create", "partial_update"}:
            return OfferWriteSerializer
        return OfferReadSerializer


class OfferDetailView(generics.RetrieveAPIView):
    """Retrieve one complete service tier."""

    queryset = OfferDetail.objects.all()
    serializer_class = DetailSerializer
    permission_classes = [IsAuthenticated]
