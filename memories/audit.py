from typing import Any

from memories.models import Capsule, CapsuleAuditLog


def record_capsule_event(
    capsule: Capsule,
    event: str,
    actor: Any = None,
    metadata: dict[str, Any] | None = None,
) -> CapsuleAuditLog:
    """
    Append a single immutable audit entry for a capsule action.

    ``actor`` should be the acting user for request-driven events; leave it
    ``None`` for background/system events (e.g. nightly article generation).
    """

    return CapsuleAuditLog.objects.create(
        capsule=capsule,
        actor=actor,
        event=event,
        metadata=metadata or {},
    )
