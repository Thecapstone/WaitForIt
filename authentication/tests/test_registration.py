import pytest


@pytest.mark.django_db
def test_register(api_client):
    response = api_client.post(
        "/api/auth/register/",
        {
            "email": "john@example.com",
            "password": "secret123",
        },
    )

    assert response.status_code == 201
