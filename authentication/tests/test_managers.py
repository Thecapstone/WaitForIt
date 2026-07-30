# Create your tests here.
import pytest

from authentication.models import User


@pytest.mark.django_db
def test_create_user():
    user = User.objects.create_user(
        email="test@example.com",
        password="password123",
    )

    assert user.email == "test@example.com"
    assert user.check_password("password123")
    assert not user.is_staff
    assert not user.is_superuser


@pytest.mark.django_db
def test_create_superuser():
    user = User.objects.create_superuser(
        email="admin@example.com",
        password="password123",
    )

    assert user.is_staff
    assert user.is_superuser


@pytest.mark.django_db
def test_create_user_requires_email():
    with pytest.raises(ValueError):
        User.objects.create_user(
            email="",
            password="password123",
        )


@pytest.mark.django_db
def test_create_user_requires_password():
    with pytest.raises(ValueError):
        User.objects.create_user(
            email="test@example.com",
            password=None,
        )
