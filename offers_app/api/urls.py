"""Explicit offer routes without undocumented root endpoints."""

from django.urls import path

from .views import OfferDetailView, OfferViewSet

urlpatterns = [
    path(
        "offers/",
        OfferViewSet.as_view({"get": "list", "post": "create"}),
        name="offers",
    ),
    path(
        "offers/<int:pk>/",
        OfferViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="offer",
    ),
    path("offerdetails/<int:pk>/", OfferDetailView.as_view(), name="offerdetail"),
]
