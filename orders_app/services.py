"""Capture purchased service data in independent order snapshots."""

from django.db import transaction
from django.shortcuts import get_object_or_404

from offers_app.models import OfferDetail

from .models import Order

SNAPSHOT_FIELDS = [
    "title",
    "revisions",
    "delivery_time_in_days",
    "price",
    "features",
    "offer_type",
]


@transaction.atomic
def create_order(customer, detail_id):
    """Copy all purchased tier data while locking its source row."""
    detail = get_object_or_404(
        OfferDetail.objects.select_for_update().select_related("offer"), pk=detail_id
    )
    values = {name: getattr(detail, name) for name in SNAPSHOT_FIELDS}
    return Order.objects.create(
        customer_user=customer, business_user=detail.offer.user, **values
    )
