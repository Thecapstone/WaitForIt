from datetime import timedelta

from django.conf import settings
from django.utils import timezone
import pytest

from authentication.tokens import (
    EmailVerificationToken,
    TokenTypes,
    generate_password_reset_token,
    generate_token,
    verify_password_reset_token,
    verify_verification_token,
)

ALGORITHM = "HS256"
EMAIL_SECRET_KEY = settings.EMAIL_SECRET_KEY


@pytest.mark.django_db
def test_generate_verification_token(user):
    token = generate_token(
        user.pk,
        timezone.now() + timedelta(hours=1),
        TokenTypes["EMAIL"],
    )

    assert token is not None

    assert EmailVerificationToken.objects.count() == 1


@pytest.mark.django_db
def test_verify_verification_token(user):
    token = generate_token(
        user.pk,
        timezone.now() + timedelta(hours=1),
        TokenTypes["EMAIL"],
    )

    payload = verify_verification_token(token)

    assert payload["type"] == TokenTypes["EMAIL"]


@pytest.mark.django_db
def test_wrong_token_type(user):
    token = generate_password_reset_token(
        user.pk,
        timezone.now() + timedelta(hours=1),
        TokenTypes["PASSWORD"],
    )

    with pytest.raises(ValueError):
        verify_verification_token(token)


@pytest.mark.django_db
def test_expired_verification_token(user):
    token = generate_token(
        user.pk,
        timezone.now() - timedelta(minutes=1),
        TokenTypes["EMAIL"],
    )

    with pytest.raises(ValueError):
        verify_verification_token(token)


@pytest.mark.django_db
def test_password_reset_token_can_only_be_used_once(user):
    token = generate_password_reset_token(
        user.pk,
        timezone.now() + timedelta(hours=1),
        TokenTypes["PASSWORD"],
    )

    verify_password_reset_token(token)

    with pytest.raises(ValueError):
        verify_password_reset_token(token)


@pytest.mark.django_db
def test_verify_email(api_client, user):
    token = generate_token(
        user.pk,
        timezone.now() + timedelta(hours=1),
        TokenTypes["EMAIL"],
    )

    response = api_client.get(f"/api/auth/verify/{token}/")

    assert response.status_code == 200

    user.refresh_from_db()

    assert user.is_verified
    assert user.is_active
