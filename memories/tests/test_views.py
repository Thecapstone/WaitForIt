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
def outsider():
    return User.objects.create_user(
        email="outsider@example.com",
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


def audit_logs_url(capsule_id):
    return f"/api/memories/{capsule_id}/audit-logs/"


def capsule_url(capsule_id):
    return f"/api/memories/{capsule_id}/"


def capsule_events(capsule):
    return list(capsule.audit_logs.values_list("action", flat=True))


class TestCreateCapsule:
    def test_records_created_event(self, api_client, creator):
        api_client.force_authenticate(user=creator)

        response = api_client.post(
            "/api/memories/",
            {"title": "My Capsule", "description": "Developer journey"},
        )

        assert response.status_code == 201, response.data
        capsule = Capsule.objects.get(title="My Capsule")
        assert "CREATED" in capsule_events(capsule)


class TestRetrieveCapsule:
    def test_records_viewed_event(self, api_client, creator, capsule):
        api_client.force_authenticate(user=creator)

        response = api_client.get(capsule_url(capsule.id))

        assert response.status_code == 200, response.data
        assert "VIEWED" in capsule_events(capsule)

    def test_does_not_record_view_when_denied(self, api_client, outsider, capsule):
        api_client.force_authenticate(user=outsider)

        response = api_client.get(capsule_url(capsule.id))

        assert response.status_code == 401
        assert capsule.audit_logs.count() == 0


class TestUpdateCapsule:
    def test_update_persists_and_records_event(self, api_client, creator, capsule):
        api_client.force_authenticate(user=creator)

        response = api_client.patch(
            capsule_url(capsule.id),
            {"title": "Renamed Journal"},
        )

        assert response.status_code == 200, response.data
        capsule.refresh_from_db()
        assert capsule.title == "Renamed Journal"
        assert "UPDATED" in capsule_events(capsule)

    def test_non_contributor_cannot_update(self, api_client, outsider, capsule):
        api_client.force_authenticate(user=outsider)

        response = api_client.patch(
            capsule_url(capsule.id),
            {"title": "Hacked"},
        )

        assert response.status_code == 401
        capsule.refresh_from_db()
        assert capsule.title == "Developer Journal"
        assert capsule.audit_logs.count() == 0


class TestCreateLog:
    def test_creates_log_for_authenticated_user(self, api_client, creator, capsule):
        api_client.force_authenticate(user=creator)

        response = api_client.post(create_log_url(capsule.id), valid_log_payload())

        assert response.status_code == 201, response.data
        assert Logs.objects.filter(capsule=capsule, creator=creator).count() == 1
        assert "LOG_ADDED" in capsule_events(capsule)

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


class TestAuditLogsEndpoint:
    def test_creator_can_read_audit_trail(self, api_client, creator, capsule):
        api_client.force_authenticate(user=creator)

        response = api_client.get(audit_logs_url(capsule.id))

        assert response.status_code == 200, response.data
        assert response.data == []

    def test_creator_sees_recorded_events(self, api_client, creator, capsule):
        api_client.force_authenticate(user=creator)
        api_client.get(capsule_url(capsule.id))
        api_client.post(create_log_url(capsule.id), valid_log_payload())

        response = api_client.get(audit_logs_url(capsule.id))

        assert response.status_code == 200, response.data
        actions = [entry["action"] for entry in response.data]
        assert actions == ["LOG_ADDED", "VIEWED"]

    def test_audit_entries_carry_entity_and_metadata(
        self, api_client, creator, capsule
    ):
        api_client.force_authenticate(user=creator)
        api_client.post(create_log_url(capsule.id), valid_log_payload())

        response = api_client.get(audit_logs_url(capsule.id))

        assert response.status_code == 200, response.data
        log_added = next(e for e in response.data if e["action"] == "LOG_ADDED")
        assert log_added["entity_type"] == "log"
        assert log_added["entity_id"] == Logs.objects.get(capsule=capsule).id
        assert log_added["metadata"]["capsule_id"] == capsule.id
        assert log_added["metadata"]["actor_id"] == creator.id
        assert "actioned_at" in log_added["metadata"]

    def test_forbidden_user_cannot_read(self, api_client, outsider, capsule):
        api_client.force_authenticate(user=outsider)

        response = api_client.get(audit_logs_url(capsule.id))

        assert response.status_code == 401

    def test_missing_capsule_returns_404(self, api_client, creator):
        api_client.force_authenticate(user=creator)

        response = api_client.get(audit_logs_url("does-not-exist"))

        assert response.status_code == 404
