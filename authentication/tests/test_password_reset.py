from datetime import timedelta

from django.utils import timezone
import pytest

from authentication.tokens import (
    TokenTypes,
    generate_password_reset_token,
)


@pytest.mark.django_db
def test_password_reset(api_client, user):
    token = generate_password_reset_token(
        user.pk,
        timezone.now() + timedelta(hours=1),
        TokenTypes["PASSWORD"],
    )

    response = api_client.post(
        f"/api/auth/password-reset/{token}/",
        {
            "token": token,
            "password": "newpassword123",
            "confirm_password": "newpassword123",
        },
    )

    assert response.status_code == 200

    user.refresh_from_db()

    assert user.check_password("newpassword123")
