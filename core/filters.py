"""Strict query parameter validation shared by list endpoints."""

from rest_framework import serializers


def query_values(serializer_class, request):
    """Ignore empty frontend controls and validate nonempty query values."""
    values = {key: value for key, value in request.query_params.items() if value != ""}
    serializer = serializer_class(data=values)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


class PositiveIdField(serializers.IntegerField):
    """Positive resource identifier used in filters."""

    def __init__(self, **kwargs):
        """Apply a positive integer bound."""
        super().__init__(min_value=1, required=False, **kwargs)
