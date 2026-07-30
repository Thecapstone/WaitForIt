from unittest.mock import patch

import pytest


@pytest.mark.django_db
def test_login_verified_user(api_client, verified_user):
    response = api_client.post(
        "/api/auth/login/",
        {
            "email": verified_user.email,
            "password": "password123",
        },
    )

    assert response.status_code == 200

    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies


@pytest.mark.django_db
def test_login_requires_verified_email(api_client, user):
    response = api_client.post(
        "/api/auth/login/",
        {
            "email": user.email,
            "password": "password123",
        },
    )

    assert response.status_code == 403


@patch("authentication.views.send_password_reset_email")
@pytest.mark.django_db
def test_forgot_password(mock_email, api_client, user):
    response = api_client.post(
        "/api/auth/forgot-password/",
        {
            "email": user.email,
        },
    )

    assert response.status_code == 200

    mock_email.assert_called_once()
