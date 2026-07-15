"""Middleware helper utilities for checking and counting active user sessions."""

from rest_framework.response import Response

from authentication.exceptions import NoSessionFingerprintError
from authentication.models import Sessions as session_db


def get_user_session(user: int, fingerprint: str) -> dict | None:
    """Retrieve an active user session dictionary if the fingerprint matches."""
    try:
        # pylint: disable=no-member
        user_session = session_db.objects.get(user_id=user)
        if user_session.device_fingerprint == fingerprint:
            return {
                "user_id": user_session.user_id,
                "device_fingerprint": fingerprint,
                "last_ip": user_session.last_ip,
            }
        return None
    except NoSessionFingerprintError as e:
        # Note: If this is used inside an standard Django HTTP middleware,
        # returning a DRF Response object directly here might cause rendering errors.
        return Response(
            {"message": str(e)},
            status=401,
        )


def count_active_user_devices(user: int) -> int:
    """Count the total number of logged-in sessions matching a specific user ID."""
    # pylint: disable=no-member
    active_sessions = session_db.objects.filter(user_id=user).count()
    if active_sessions >= 1:
        return active_sessions
    return 0
