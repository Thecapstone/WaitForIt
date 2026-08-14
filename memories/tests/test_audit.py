import pytest

from authentication.models import User
from memories.audit import record_capsule_event
from memories.models import Capsule, CapsuleAuditLog

pytestmark = pytest.mark.django_db


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


class TestCapsuleAuditLogModel:
    def test_creates_audit_entry_with_actor(self, capsule, creator):
        entry = record_capsule_event(
            capsule,
            CapsuleAuditLog.Event.CREATED,
            actor=creator,
        )

        assert entry.capsule == capsule
        assert entry.actor == creator
        assert entry.event == CapsuleAuditLog.Event.CREATED
        assert entry.metadata == {}

    def test_actor_is_nullable_for_system_events(self, capsule):
        entry = record_capsule_event(
            capsule,
            CapsuleAuditLog.Event.ARTICLE_GENERATED,
        )

        assert entry.actor is None
        assert entry.event == CapsuleAuditLog.Event.ARTICLE_GENERATED

    def test_metadata_captured(self, capsule, creator):
        entry = record_capsule_event(
            capsule,
            CapsuleAuditLog.Event.UPDATED,
            actor=creator,
            metadata={"field": "title"},
        )

        assert entry.metadata == {"field": "title"}

    def test_events_ordered_newest_first(self, capsule, creator):
        record_capsule_event(capsule, CapsuleAuditLog.Event.CREATED, actor=creator)
        record_capsule_event(capsule, CapsuleAuditLog.Event.VIEWED, actor=creator)

        latest = capsule.audit_logs.first()

        assert latest.event == CapsuleAuditLog.Event.VIEWED

    def test_all_expected_event_choices_exist(self):
        expected = {
            "CREATED",
            "VIEWED",
            "UPDATED",
            "LOG_ADDED",
            "ARTICLE_GENERATED",
            "MEMBER_ADDED",
            "MEMBER_REMOVED",
            "CONTRIBUTOR_ADDED",
            "CONTRIBUTOR_REMOVED",
        }

        assert set(CapsuleAuditLog.Event.values) == expected
