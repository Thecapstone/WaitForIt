from django.core.cache import cache
import pytest

from authentication.models import Sessions
from authentication.session_cache import get_active_session, session_cache_key


@pytest.mark.django_db
def test_get_active_session_falls_back_to_db_for_invalid_cached_datetime(
    verified_user,
):
    session = Sessions.objects.create(
        user_id=verified_user,
        session_token="refresh-token",
        device_fingerprint="fingerprint",
        last_ip="127.0.0.1",
    )
    cache.set(
        session_cache_key(verified_user.id),
        {
            "id": session.id,
            "user_id": verified_user.id,
            "session_token": session.session_token,
            "session_version": session.session_version,
            "device_fingerprint": session.device_fingerprint,
            "last_ip": session.last_ip,
            "last_active": "not-a-datetime",
            "created_at": session.created_at.isoformat(),
        },
        timeout=60,
    )

    active_session = get_active_session(verified_user.id, token="refresh-token")

    assert active_session.id == session.id
    assert cache.get(session_cache_key(verified_user.id))["last_active"] != (
        "not-a-datetime"
    )
