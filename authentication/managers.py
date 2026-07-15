from typing import TYPE_CHECKING

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import UserManager as DjangoUserManager

if TYPE_CHECKING:
    # Forward reference to avoid circular import
    pass


class UserManager(DjangoUserManager["User"]):
    """Custom manager for the User model."""

    def _create_user(self, email: str, password: str | None, **extra_fields):
        """
        Create and save a user with the given email and password.
        """
        if not email:
            msg = "The given email must be set"
            raise ValueError(msg)
        if not password:
            msg = "Please input a valid password"
            raise ValueError(msg)
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):  # type: ignore[override]
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):  # type: ignore[override]
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            msg = "Superuser must have is_staff=True."
            raise ValueError(msg)
        if extra_fields.get("is_superuser") is not True:
            msg = "Superuser must have is_superuser=True."
            raise ValueError(msg)

        return self._create_user(email, password, **extra_fields)

    def capstone(self, email: str, password: str | None = None, **extra_fields):
        """Create a capstone user with the given email and password."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_testuser(self, email: str, *args: str, **kwargs):
        # args = ["a", "b", "c"]
        # *args =  testing(a, b, c)

        # kwargs = {"a": 1, "b": 2, "c": 3}
        # **kwargs = testing(a=1, b=2, c=3)
        """Create a testing user with the given email."""
        return self._create_user(email, None, **kwargs)
