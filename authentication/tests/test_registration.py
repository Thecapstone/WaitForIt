import pytest


@pytest.mark.django_db
def test_register(api_client, monkeypatch):
    monkeypatch.setattr(
        "authentication.views.send_user_verification_email",
        lambda user: True,
    )
    response = api_client.post(
        "/api/auth/register/",
        {
            "email": "john@example.com",
            "password": "secret123",
        },
    )

    assert response.status_code == 201
