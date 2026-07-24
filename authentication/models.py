from typing import ClassVar
from uuid import uuid4

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from authentication.managers import UserManager

# Create your models here.


class User(AbstractUser):
    class Roles(models.TextChoices):
        USER = "user", "Regular User"
        ADMIN = "admin", "Administrator"
        TESTER = "tester", "Test User"

    role = models.CharField(max_length=15, choices=Roles.choices, default=Roles.USER)
    username = None
    first_name = None
    last_name = None

    email = models.EmailField(_("email address"), unique=True)
    password = models.TextField(_("password"), unique=True)
    verification_email_sent_at = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    last_login_ip = models.CharField(max_length=30, null=True, blank=True)
    is_premium = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"pk": self.pk})

    objects: ClassVar[UserManager] = UserManager()


class Sessions(models.Model):
    user_id = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="session_token"
    )
    session_token = models.TextField()
    device_fingerprint = models.TextField()
    session_version = models.IntegerField(default=0)
    last_ip = models.TextField()
    payload_data = models.TextField()
    last_active = models.DateTimeField(auto_now=True)


class PasswordResetToken(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="password_reset_token"
    )
    jti = models.UUIDField(default=uuid4, unique=True, editable=False)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_used(self):
        return self.used_at is not None

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at


class EmailVerificationToken(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="email_verification_token"
    )
    jti = models.UUIDField(default=uuid4, unique=True, editable=False)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_used(self):
        return self.used_at is not None

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at
