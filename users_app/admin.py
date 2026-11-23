"""Account and profile administration."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, UserProfile


class ProfileInline(admin.StackedInline):
    """Expose the automatically created account profile."""

    model = UserProfile
    can_delete = False
    extra = 0


@admin.register(User)
class AccountAdmin(UserAdmin):
    """Standard account management including profile data."""

    inlines = [ProfileInline]


@admin.register(UserProfile)
class ProfileAdmin(admin.ModelAdmin):
    """Searchable role-based profile management."""

    list_display = ["user", "type", "location"]
    list_filter = ["type"]
    search_fields = ["user__username", "location"]
