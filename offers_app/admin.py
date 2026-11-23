"""Offer administration with readable tier data."""

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

from .models import Offer, OfferDetail


class TierFormSet(BaseInlineFormSet):
    """Preserve all three service tiers during administrative edits."""

    def clean(self):
        """Require exactly one valid form for each tier."""
        super().clean()
        if any(self.errors):
            return
        active = [
            form.cleaned_data
            for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get("DELETE")
        ]
        types = [item.get("offer_type") for item in active]
        if len(types) != 3 or set(types) != {"basic", "standard", "premium"}:
            raise ValidationError("An offer must have exactly three distinct tiers.")


class DetailInline(admin.TabularInline):
    """Inspect tier data alongside an offer."""

    model = OfferDetail
    formset = TierFormSet
    extra = 0
    min_num = 3
    max_num = 3


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    """Search and inspect business service offerings."""

    list_display = ["title", "user", "updated_at"]
    search_fields = ["title", "user__username"]
    inlines = [DetailInline]
