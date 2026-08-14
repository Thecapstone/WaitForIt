import pytest
from rest_framework.test import APIClient

from authentication.models import User
from memories.models import Capsule, Logs

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def creator():
    return User.objects.create_user(
        email="creator@example.com",
        password="password123",
    )


@pytest.fixture
def capsule(creator):
    return Capsule.objects.create(
        title="Developer Journal",
        description="Building WaitForIt",
        creator=creator,
    )


def valid_log_payload():
    return {
        "title": "Added JWT auth",
        "description": "Introduced an extra auth layer for the internal API.",
        "code_language": "Python",
        "code_framework": "Django",
    }


def create_log_url(capsule_id):
    return f"/api/memories/{capsule_id}/create-log/"


class TestCreateLog:
    def test_creates_log_for_authenticated_user(self, api_client, creator, capsule):
        api_client.force_authenticate(user=creator)

        response = api_client.post(create_log_url(capsule.id), valid_log_payload())

        assert response.status_code == 201, response.data
        assert Logs.objects.filter(capsule=capsule, creator=creator).count() == 1

    def test_rejects_missing_capsule(self, api_client, creator):
        api_client.force_authenticate(user=creator)

        response = api_client.post(
            create_log_url("does-not-exist"), valid_log_payload()
        )

        assert response.status_code == 404

    def test_unauthenticated_request(self, api_client, capsule):
        response = api_client.post(create_log_url(capsule.id), valid_log_payload())

        assert response.status_code in (401, 403)

    def test_invalid_payload_returns_400(self, api_client, creator, capsule):
        api_client.force_authenticate(user=creator)

        response = api_client.post(
            create_log_url(capsule.id),
            {"title": "Missing everything else"},
        )

        assert response.status_code == 400

    def test_get_method_not_allowed(self, api_client, creator, capsule):
        api_client.force_authenticate(user=creator)

        response = api_client.get(create_log_url(capsule.id))

        assert response.status_code == 405
