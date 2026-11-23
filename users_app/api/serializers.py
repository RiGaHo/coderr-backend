"""Authentication and profile request/response contracts."""

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from core.validation import StrictFieldsMixin, validate_image
from users_app.models import User, UserProfile
from users_app.services import register_user, update_profile


class RegistrationSerializer(StrictFieldsMixin, serializers.ModelSerializer):
    """Validate new accounts without exposing privileged account fields."""

    repeated_password = serializers.CharField(write_only=True)
    type = serializers.ChoiceField(choices=UserProfile.TYPES, write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "repeated_password", "type"]
        extra_kwargs = {"password": {"write_only": True, "trim_whitespace": False}}

    def validate_email(self, value):
        """Enforce case-insensitive account email uniqueness."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value.lower()

    def validate(self, attrs):
        """Validate password confirmation and Django password policy."""
        if attrs["password"] != attrs["repeated_password"]:
            raise serializers.ValidationError(
                {"repeated_password": "Passwords differ."}
            )
        user = User(username=attrs["username"], email=attrs["email"])
        try:
            validate_password(attrs["password"], user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": error.messages}) from error
        return attrs

    def create(self, validated_data):
        """Delegate transactional account creation."""
        return register_user(validated_data)


class LoginSerializer(StrictFieldsMixin, serializers.Serializer):
    """Authenticate credentials with the documented 400 error behavior."""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        """Accept only active users with a valid password."""
        user = authenticate(request=self.context.get("request"), **attrs)
        if user is None:
            raise serializers.ValidationError("Invalid username or password.")
        return {"user": user}


class ProfileSerializer(StrictFieldsMixin, serializers.ModelSerializer):
    """Complete profile representation with restricted editable fields."""

    user = serializers.IntegerField(source="user_id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    first_name = serializers.CharField(
        source="user.first_name", required=False, allow_blank=True
    )
    last_name = serializers.CharField(
        source="user.last_name", required=False, allow_blank=True
    )
    email = serializers.EmailField(source="user.email", required=False)

    class Meta:
        model = UserProfile
        fields = [
            "user",
            "username",
            "first_name",
            "last_name",
            "file",
            "location",
            "tel",
            "description",
            "working_hours",
            "type",
            "email",
            "created_at",
            "uploaded_at",
        ]
        read_only_fields = ["type", "created_at", "uploaded_at"]

    def validate_email(self, value):
        """Prevent account email collisions on profile updates."""
        users = User.objects.filter(email__iexact=value).exclude(
            pk=self.instance.user_id
        )
        if users.exists():
            raise serializers.ValidationError("This email is already registered.")
        return value.lower()

    def validate_file(self, value):
        """Validate uploaded profile pictures."""
        return validate_image(value)

    def update(self, instance, validated_data):
        """Save profile and account changes atomically."""
        return update_profile(instance, validated_data)


class ProfileListSerializer(ProfileSerializer):
    """Omit email addresses from directory listings."""

    class Meta(ProfileSerializer.Meta):
        fields = [name for name in ProfileSerializer.Meta.fields if name != "email"]
