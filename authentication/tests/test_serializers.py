import pytest

from authentication.serializers import UserCreateSerializer


@pytest.mark.django_db
def test_registration_serializer_valid():

    serializer = UserCreateSerializer(
        data={
            "email": "john@example.com",
            "password": "secret123",
        }
    )

    assert serializer.is_valid()


@pytest.mark.django_db
def test_duplicate_email():

    serializer = UserCreateSerializer(
        data={
            "email": "john@example.com",
            "password": "secret123",
        }
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()

    serializer = UserCreateSerializer(
        data={
            "email": "john@example.com",
            "password": "another",
        }
    )

    assert not serializer.is_valid()
    assert "email" in serializer.errors
