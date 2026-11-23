"""Review and platform-statistic routes."""

from django.urls import path

from .views import BaseInfoView, ReviewViewSet

urlpatterns = [
    path(
        "reviews/",
        ReviewViewSet.as_view({"get": "list", "post": "create"}),
        name="reviews",
    ),
    path(
        "reviews/<int:pk>/",
        ReviewViewSet.as_view({"patch": "partial_update", "delete": "destroy"}),
        name="review",
    ),
    path("base-info/", BaseInfoView.as_view(), name="base-info"),
]
