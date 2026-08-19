"""Redis-backed helpers for active sessions and login limits."""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.utils import timezone
from django.utils.dateparse import parse_datetime
import jwt
from rest_framework_simplejwt.exceptions import AuthenticationFailed

from authentication.models import Sessions

SESSION_IDLE_TIMEOUT = timedelta(days=7)
SESSION_ABSOLUTE_TIMEOUT = timedelta(days=30)
LOGIN_ATTEMPT_LIMIT = 4
LOGIN_LOCKOUT_SECONDS = 15 * 60


def session_cache_key(user_id: int | str) -> str:
    return f"session:user:{user_id}"


def login_attempt_cache_key(email: str) -> str:
    return f"auth:login-attempts:{email.strip().lower()}"


def cache_session(session: Sessions) -> None:
    cache.set(
        session_cache_key(session.user_id_id),
        {
            "id": session.id,
            "user_id": session.user_id_id,
            "session_token": session.session_token,
            "session_version": session.session_version,
            "device_fingerprint": session.device_fingerprint,
            "last_ip": session.last_ip,
            "last_active": session.last_active.isoformat(),
            "created_at": session.created_at.isoformat(),
        },
        timeout=int(SESSION_ABSOLUTE_TIMEOUT.total_seconds()),
    )


def clear_cached_session(user_id: int | str) -> None:
    cache.delete(session_cache_key(user_id))


def _parse_datetime(value):
    if not value:
        return None
    if hasattr(value, "tzinfo"):
        parsed = value
    else:
        parsed = parse_datetime(str(value))
        if parsed is None:
            raise ValueError(f"Invalid cached datetime: {value!r}")
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def get_active_session(user_id: int | str, token: str | None = None) -> Sessions:
    now = timezone.now()
    cached = cache.get(session_cache_key(user_id))

    if cached:
        try:
            last_active = _parse_datetime(cached.get("last_active"))
            created_at = _parse_datetime(cached.get("created_at"))
        except (TypeError, ValueError):
            clear_cached_session(user_id)
        else:
            if token and cached.get("session_token") != token:
                raise AuthenticationFailed("Session token has been revoked.")
            if last_active and now - last_active > SESSION_IDLE_TIMEOUT:
                invalidate_session(user_id)
                raise AuthenticationFailed(
                    "Session expired after 7 days of inactivity."
                )
            if created_at and now - created_at > SESSION_ABSOLUTE_TIMEOUT:
                invalidate_session(user_id)
                raise AuthenticationFailed("Session expired after 30 days.")

            Sessions.objects.filter(id=cached["id"]).update(last_active=now)
            cached["last_active"] = now.isoformat()
            cache.set(
                session_cache_key(user_id),
                cached,
                timeout=int(SESSION_ABSOLUTE_TIMEOUT.total_seconds()),
            )
            return Sessions(
                id=cached["id"],
                user_id_id=cached["user_id"],
                session_token=cached["session_token"],
                session_version=cached["session_version"],
                device_fingerprint=cached["device_fingerprint"],
                last_ip=cached["last_ip"],
                last_active=now,
                created_at=created_at,
            )

    try:
        session = Sessions.objects.get(user_id_id=user_id)
    except Sessions.DoesNotExist as err:
        raise AuthenticationFailed("User session does not exist.") from err

    if token and session.session_token != token:
        raise AuthenticationFailed("Session token has been revoked.")
    if now - session.last_active > SESSION_IDLE_TIMEOUT:
        invalidate_session(user_id)
        raise AuthenticationFailed("Session expired after 7 days of inactivity.")
    if now - session.created_at > SESSION_ABSOLUTE_TIMEOUT:
        invalidate_session(user_id)
        raise AuthenticationFailed("Session expired after 30 days.")

    session.last_active = now
    session.save(update_fields=["last_active"])
    cache_session(session)
    return session


def invalidate_session(user_id: int | str) -> None:
    Sessions.objects.filter(user_id_id=user_id).update(
        session_token="",
        last_ip="",
        session_version=models.F("session_version") + 1,
        device_fingerprint="",
        last_active=timezone.now(),
    )
    clear_cached_session(user_id)


def decode_session_user_id(session_token: str) -> int:
    payload = jwt.decode(
        session_token,
        settings.SESSION_SECRET,
        algorithms=["HS256"],
    ).get("payload", {})
    user_id = payload.get("user_id")
    if not user_id:
        raise AuthenticationFailed("Invalid session token payload data.")
    return int(user_id)


def login_lockout_ttl(email: str) -> int:
    key = login_attempt_cache_key(email)
    return cache.ttl(key) if hasattr(cache, "ttl") else LOGIN_LOCKOUT_SECONDS


def failed_login_count(email: str) -> int:
    return int(cache.get(login_attempt_cache_key(email), 0) or 0)


def record_failed_login(email: str) -> int:
    key = login_attempt_cache_key(email)
    attempts = cache.get(key, 0) + 1
    cache.set(key, attempts, timeout=LOGIN_LOCKOUT_SECONDS)
    return attempts


def clear_failed_login(email: str) -> None:
    cache.delete(login_attempt_cache_key(email))
