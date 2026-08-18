from datetime import UTC, datetime
from typing import Any

from memories.models import Capsule, CapsuleAuditLog


def record_capsule_event(
    capsule: Capsule,
    action: str,
    entity_type: str,
    entity_id: str,
    actor: Any = None,
    metadata: dict[str, Any] | None = None,
) -> CapsuleAuditLog:
    """
    Append a single immutable audit entry for a capsule action.

    ``actor`` should be the acting user for request-driven events; leave it
    ``None`` for background/system events (e.g. nightly article generation).

    Metadata is enriched with the actioned-at timestamp plus the capsule and
    actor ids so each entry stays self-contained even if the source rows are
    later deleted.
    """

    enriched = {
        "actioned_at": datetime.now(UTC).isoformat(),
        "capsule_id": capsule.id,
        "actor_id": actor.id if actor else None,
    }
    if metadata:
        enriched.update(metadata)

    return CapsuleAuditLog.objects.create(
        capsule=capsule,
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata=enriched,
    )
