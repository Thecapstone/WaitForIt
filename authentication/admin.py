"""Django admin customization for the User model."""

from django.contrib import admin

from authentication.models import User


# Register your models here.
# pylint: disable=too-few-public-methods
@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    """Custom admin interface for the User model."""

    pass
