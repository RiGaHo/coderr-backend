"""Authentication and profile routes."""

from django.urls import path

from .views import LoginView, ProfileListView, ProfileView, RegistrationView

urlpatterns = [
    path("registration/", RegistrationView.as_view(), name="registration"),
    path("login/", LoginView.as_view(), name="login"),
    path("profile/<int:pk>/", ProfileView.as_view(), name="profile"),
    path(
        "profiles/business/",
        ProfileListView.as_view(role="business"),
        name="business-profiles",
    ),
    path(
        "profiles/customer/",
        ProfileListView.as_view(role="customer"),
        name="customer-profiles",
    ),
]
