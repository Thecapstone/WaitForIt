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
            CapsuleAuditLog.Action.CREATED,
            entity_type=CapsuleAuditLog.EntityType.CAPSULE,
            entity_id=capsule.id,
            actor=creator,
        )

        assert entry.capsule == capsule
        assert entry.actor == creator
        assert entry.action == CapsuleAuditLog.Action.CREATED
        assert entry.entity_type == CapsuleAuditLog.EntityType.CAPSULE
        assert entry.entity_id == capsule.id

    def test_actor_is_nullable_for_system_events(self, capsule):
        entry = record_capsule_event(
            capsule,
            CapsuleAuditLog.Action.ARTICLE_GENERATED,
            entity_type=CapsuleAuditLog.EntityType.ARTICLE,
            entity_id="article-1",
        )

        assert entry.actor is None
        assert entry.action == CapsuleAuditLog.Action.ARTICLE_GENERATED

    def test_metadata_is_auto_enriched(self, capsule, creator):
        entry = record_capsule_event(
            capsule,
            CapsuleAuditLog.Action.UPDATED,
            entity_type=CapsuleAuditLog.EntityType.CAPSULE,
            entity_id=capsule.id,
            actor=creator,
            metadata={"field": "title"},
        )

        assert entry.metadata["capsule_id"] == capsule.id
        assert entry.metadata["actor_id"] == creator.id
        assert entry.metadata["field"] == "title"
        assert "actioned_at" in entry.metadata

    def test_events_ordered_newest_first(self, capsule, creator):
        record_capsule_event(
            capsule,
            CapsuleAuditLog.Action.CREATED,
            entity_type=CapsuleAuditLog.EntityType.CAPSULE,
            entity_id=capsule.id,
            actor=creator,
        )
        record_capsule_event(
            capsule,
            CapsuleAuditLog.Action.VIEWED,
            entity_type=CapsuleAuditLog.EntityType.CAPSULE,
            entity_id=capsule.id,
            actor=creator,
        )

        latest = capsule.audit_logs.first()

        assert latest.action == CapsuleAuditLog.Action.VIEWED

    def test_all_expected_action_choices_exist(self):
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

        assert set(CapsuleAuditLog.Action.values) == expected

    def test_all_expected_entity_types_exist(self):
        expected = {"capsule", "log", "article", "user"}

        assert set(CapsuleAuditLog.EntityType.values) == expected

    def test_deleting_capsule_does_not_delete_audit_rows(self, capsule, creator):
        record_capsule_event(
            capsule,
            CapsuleAuditLog.Action.CREATED,
            entity_type=CapsuleAuditLog.EntityType.CAPSULE,
            entity_id=capsule.id,
            actor=creator,
        )
        capsule_id = capsule.id

        capsule.delete()

        assert CapsuleAuditLog.objects.count() == 1
        remaining = CapsuleAuditLog.objects.first()
        assert remaining.entity_id == capsule_id
