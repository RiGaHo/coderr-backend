"""Transactional offer creation and tier-preserving updates."""

from django.db import transaction

from .models import Offer, OfferDetail


@transaction.atomic
def create_offer(user, data):
    """Create an offer and all validated tiers as one transaction."""
    details = data.pop("details")
    offer = Offer.objects.create(user=user, **data)
    for detail in details:
        OfferDetail.objects.create(offer=offer, **detail)
    return offer


@transaction.atomic
def update_offer(offer, data):
    """Serialize concurrent mutations and preserve existing detail identities."""
    offer = Offer.objects.select_for_update().get(pk=offer.pk)
    details = data.pop("details", [])
    for key, value in data.items():
        setattr(offer, key, value)
    offer.save()
    for detail in details:
        tier = detail.pop("offer_type")
        OfferDetail.objects.filter(offer=offer, offer_type=tier).update(**detail)
    return offer
