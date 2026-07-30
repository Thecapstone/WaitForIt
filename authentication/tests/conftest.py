import pytest
from rest_framework.test import APIClient

from authentication.models import User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return User.objects.create_user(
        email="user@example.com",
        password="password123",
    )


@pytest.fixture
def verified_user():
    user = User.objects.create_user(
        email="verified@example.com",
        password="password123",
    )
    user.is_verified = True
    user.is_active = True
    user.save()
    return user
