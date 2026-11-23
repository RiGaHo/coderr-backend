"""Authentication and user-profile endpoints."""

from django.db import IntegrityError
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from users_app.models import UserProfile
from users_app.services import auth_response

from .permissions import IsProfileOwnerOrReadOnly
from .serializers import (
    LoginSerializer,
    ProfileListSerializer,
    ProfileSerializer,
    RegistrationSerializer,
)


class RegistrationView(generics.GenericAPIView):
    """Create a customer or business account."""

    serializer_class = RegistrationSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        """Return a token and public account identity after registration."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = serializer.save()
        except IntegrityError as error:
            raise ValidationError("Username or email is already registered.") from error
        return Response(auth_response(user), status=status.HTTP_201_CREATED)


class LoginView(generics.GenericAPIView):
    """Exchange valid credentials for a persistent DRF token."""

    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        """Return the documented login response."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(auth_response(serializer.validated_data["user"]))


class ProfileView(generics.RetrieveUpdateAPIView):
    """Read profiles and allow owners to update their editable fields."""

    queryset = UserProfile.objects.select_related("user")
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated, IsProfileOwnerOrReadOnly]
    lookup_field = "user_id"
    lookup_url_kwarg = "pk"
    http_method_names = ["get", "patch", "head", "options"]

    def perform_update(self, serializer):
        """Translate a concurrent email collision into a validation error."""
        try:
            serializer.save()
        except IntegrityError as error:
            raise ValidationError(
                {"email": "This email is already registered."}
            ) from error


class ProfileListView(generics.ListAPIView):
    """List directory profiles for a role supplied by the URL configuration."""

    queryset = UserProfile.objects.select_related("user")
    serializer_class = ProfileListSerializer
    permission_classes = [IsAuthenticated]
    role = None

    def get_queryset(self):
        """Return only the requested role."""
        return self.queryset.filter(type=self.role)
