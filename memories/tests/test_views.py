from datetime import timedelta

from django.utils import timezone
import pytest
from rest_framework.test import APIClient

from authentication.models import User
from memories.models import Capsule, Logs

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return User.objects.create_user(email="capsule-owner@example.com", password="pass")


@pytest.fixture
def other_user():
    return User.objects.create_user(email="outsider@example.com", password="pass")


def make_capsule(user, **overrides):
    defaults = {
        "title": "Build Log",
        "description": "Project notes",
        "creator": user,
        "private": True,
        "maturity_date": timezone.now() + timedelta(days=1),
    }
    defaults.update(overrides)
    return Capsule.objects.create(**defaults)


def test_capsule_view_returns_404_when_parent_capsule_does_not_exist(api_client, user):
    api_client.force_authenticate(user=user)

    response = api_client.get("/api/memories/missing-id/view/")

    assert response.status_code == 404


def test_private_immature_capsule_rejects_non_member(api_client, user, other_user):
    capsule = make_capsule(user)
    api_client.force_authenticate(user=other_user)

    response = api_client.get(f"/api/memories/{capsule.id}/view/")

    assert response.status_code == 401


def test_public_immature_capsule_returns_preview_without_logs(
    api_client, user, other_user
):
    capsule = make_capsule(user, private=False)
    Logs.objects.create(
        capsule=capsule,
        creator=user,
        stamp="hidden-log",
        title="Hidden",
        description="Locked until maturity",
    )
    api_client.force_authenticate(user=other_user)

    response = api_client.get(f"/api/memories/{capsule.id}/view/")

    assert response.status_code == 200
    assert response.data["data"]["title"] == capsule.title
    assert "logs" not in response.data["data"]
    assert "teasers" in response.data["data"]


def test_mature_private_capsule_member_gets_full_archive(api_client, user, other_user):
    capsule = make_capsule(
        user,
        maturity_date=timezone.now() - timedelta(minutes=1),
    )
    capsule.member.add(other_user)
    Logs.objects.create(
        capsule=capsule,
        creator=user,
        stamp="visible-log",
        title="Visible",
        description="Unlocked",
    )
    api_client.force_authenticate(user=other_user)

    response = api_client.get(f"/api/memories/{capsule.id}/view/")

    assert response.status_code == 200
    assert response.data["data"]["logs"][0]["title"] == "Visible"
    assert "articles" in response.data["data"]


def test_logs_endpoint_requires_existing_mature_capsule(api_client, user):
    capsule = make_capsule(user)
    api_client.force_authenticate(user=user)

    response = api_client.get(f"/api/memories/{capsule.id}/logs/")
    missing_response = api_client.get("/api/memories/missing-id/logs/")

    assert response.status_code == 403
    assert missing_response.status_code == 404


def test_create_log_uses_parent_capsule_id(api_client, user, monkeypatch):
    capsule = make_capsule(user)
    api_client.force_authenticate(user=user)
    monkeypatch.setattr(
        "memories.serializers.dispatch_log_created", lambda log_id: None
    )

    response = api_client.post(
        f"/api/memories/{capsule.id}/create-log/",
        {
            "title": "Day one",
            "description": "Set up project",
            "code_language": "Python",
            "code_framework": "Django",
        },
    )

    assert response.status_code == 201
    assert Logs.objects.get(title="Day one").capsule == capsule
