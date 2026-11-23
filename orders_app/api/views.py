"""Personal order lists, creation, status changes and business counts."""

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from orders_app.models import Order
from users_app.models import UserProfile

from .permissions import OrderPermission
from .serializers import OrderCreateSerializer, OrderSerializer, OrderUpdateSerializer


class OrderViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Expose only the documented order operations."""

    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, OrderPermission]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        """Hide unrelated orders from both lists and object lookups."""
        user = self.request.user
        return self.queryset.filter(Q(customer_user=user) | Q(business_user=user))

    def get_serializer_class(self):
        """Select narrow mutation schemas."""
        return {
            "create": OrderCreateSerializer,
            "partial_update": OrderUpdateSerializer,
        }.get(self.action, OrderSerializer)


class OrderCountView(APIView):
    """Count one documented status for a valid business account."""

    permission_classes = [IsAuthenticated]
    order_status = "in_progress"

    def get(self, request, business_user_id):
        """Keep the documented completed key and its frontend-compatible alias."""
        get_object_or_404(UserProfile, user_id=business_user_id, type="business")
        count = Order.objects.filter(
            business_user_id=business_user_id, status=self.order_status
        ).count()
        result = {"order_count": count}
        if self.order_status == "completed":
            result["completed_order_count"] = count
        return Response(result)
