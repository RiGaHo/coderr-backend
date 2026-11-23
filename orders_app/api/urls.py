"""Order routes without retrieval or deletion operations."""

from django.urls import path

from .views import OrderCountView, OrderViewSet

urlpatterns = [
    path(
        "orders/",
        OrderViewSet.as_view({"get": "list", "post": "create"}),
        name="orders",
    ),
    path(
        "orders/<int:pk>/",
        OrderViewSet.as_view({"patch": "partial_update"}),
        name="order",
    ),
    path(
        "order-count/<int:business_user_id>/",
        OrderCountView.as_view(),
        name="order-count",
    ),
    path(
        "completed-order-count/<int:business_user_id>/",
        OrderCountView.as_view(order_status="completed"),
        name="completed-order-count",
    ),
]
