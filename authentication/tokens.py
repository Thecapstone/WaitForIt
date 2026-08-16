"""Custom JWT authentication backend handling cookie-based tokens."""

import hashlib
from secrets import compare_digest
from uuid import uuid4

from django.conf import settings
from django.utils import timezone
from ipware import get_client_ip
import jwt
from rest_framework import permissions
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import AccessToken
from user_agents.parsers import parse

from authentication.models import (
    EmailVerificationToken,
    PasswordResetToken,
    User as user_db,
)
from authentication.session_cache import get_active_session

ACCESS_SECRET = settings.ACCESS_SECRET
SESSION_SECRET = settings.SESSION_SECRET
EMAIL_SECRET_KEY = settings.EMAIL_SECRET_KEY
ADMIN_BOOTSTRAP_TOKEN = settings.ADMIN_KEY

TokenTypes = {"EMAIL": "email_verification", "PASSWORD": "password_reset"}
ALGORITHM = "HS256"


def ensure_aware_datetime(value):
    if timezone.is_naive(value):
        return timezone.make_aware(value, timezone.get_current_timezone())
    return value


# pylint: disable=too-few-public-methods
class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        token = request.COOKIES.get("access_token")

        if not token:
            return super().authenticate(request)

        validated_token = self.get_validated_token(token)
        user = self.get_user(validated_token)
        get_active_session(user.id, request.COOKIES.get("refresh_token"))

        return user, validated_token


def create_user_agent(u_agent: str, ip: str, fingerprint: str) -> str:
    """Generate a stable, hashed device fingerprint from IP and User Agent."""
    ip_addr = ".".join(ip.split(".")[:2])
    user_agent = parse(u_agent)
    stable_string = f"{user_agent.os.family}--{user_agent.browser.family}--{user_agent.is_mobile}--{ip_addr}--{fingerprint}"

    return hashlib.sha256(stable_string.encode("utf-8")).hexdigest()


class HasBootstrapToken(permissions.BasePermission):
    """Allows access only if the client provides the correct secret master key."""

    def is_allowed(self, request, view):
        # Fetch the secret token from the server environment
        secret_key = ADMIN_BOOTSTRAP_TOKEN
        if not secret_key:
            return False  # Secure by default if env variable is missing

        # Check for matching HTTP Header (e.g., 'X-Bootstrap-Token: my-secret-key')
        client_token = request.headers.get("X-Bootstrap-Token")
        return compare_digest(client_token or "", secret_key or "")


def session_token(user_id: int, role: str, session_version: int, request) -> str:
    """Build and hash a tracking payload tracking user session versions."""
    ip_address, _ = get_client_ip(request)
    user_agent = request.META.get("HTTP_USER_AGENT", "")
    fingerprint = hashlib.sha256(uuid4().bytes).hexdigest()
    active_devices = create_user_agent(user_agent, ip_address, fingerprint)
    payload = {
        "user_id": user_id,
        "role": role,
        "ip_address": ip_address,
        "fingerprint": fingerprint,
        "session_version": session_version,
        "active_devices": active_devices,
    }
    # return hashlib.sha256(str(payload).encode("utf-8")).hexdigest()
    return jwt.encode({"payload": payload}, SESSION_SECRET, algorithm=ALGORITHM)


def access_token(session_token: str) -> str:
    """Decodes a valid session token and generates a short-lived access token."""
    try:
        # 1. Decode and verify the session token
        decoded_session = jwt.decode(
            session_token, SESSION_SECRET, algorithms=[ALGORITHM]
        )
        session_payload = decoded_session.get("payload", {})

        # 2. Extract necessary user identifiers
        user_id = session_payload.get("user_id")
        user = user_db.objects.get(id=user_id)
        session = get_active_session(user_id, token=session_token)
        session_version = session_payload.get("session_version")
        role = session_payload.get("role")

        if not user_id or not role:
            raise ValueError("Invalid session token payload data.")

        if session_version != session.session_version:
            raise AuthenticationFailed("Token has been revoked.")
        token = AccessToken.for_user(user)

        token["user_id"] = str(user.id)
        token["role"] = role
        token["session_version"] = session_version

        return str(token)

        # 3. Define access token payload with expiration (e.g., 15 minutes)
    except user_db.DoesNotExist as err:
        raise AuthenticationFailed("User does not exist.") from err

    except jwt.ExpiredSignatureError as err:
        raise AuthenticationFailed(
            "Session token has expired. Please log in again."
        ) from err

    except jwt.InvalidTokenError as err:
        raise AuthenticationFailed("Invalid session token.") from err


def generate_token(user_id, exp, token_type) -> str:
    """Generate a unique token for email verification and password reset."""
    jti = str(uuid4())

    EmailVerificationToken.objects.create(
        user_id=user_id,
        jti=jti,
        expires_at=exp,
    )

    payload = {
        "user_id": str(user_id),
        "type": token_type,
        "jti": jti,
        "exp": exp,
    }
    return jwt.encode(payload, EMAIL_SECRET_KEY, algorithm=ALGORITHM)


def verify_verification_token(token):
    """Verify an email verification token."""

    try:
        payload = jwt.decode(
            token,
            EMAIL_SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        if payload.get("type") != TokenTypes["EMAIL"]:
            raise ValueError("Invalid token type.")

        verification_token = EmailVerificationToken.objects.select_related("user").get(
            jti=payload["jti"]
        )

        if verification_token.used_at is not None:
            raise ValueError("This verification link has already been used.")

        if ensure_aware_datetime(verification_token.expires_at) <= timezone.now():
            raise ValueError("Verification link has expired.")

        verification_token.used_at = timezone.now()
        verification_token.save(update_fields=["used_at"])

        return payload

    except EmailVerificationToken.DoesNotExist as err:
        raise ValueError("Invalid verification token.") from err

    except jwt.ExpiredSignatureError as err:
        raise ValueError("Verification link has expired.") from err

    except jwt.InvalidTokenError as err:
        raise ValueError("Invalid verification token.") from err


def generate_password_reset_token(user_id, exp, token_type) -> str:
    """Generate and persist a one-time password reset token."""

    jti = uuid4()

    PasswordResetToken.objects.create(
        user_id=user_id,
        jti=jti,
        expires_at=exp,
    )

    payload = {
        "user_id": user_id,
        "type": token_type,
        "jti": str(jti),
        "exp": exp,
    }

    return jwt.encode(payload, EMAIL_SECRET_KEY, algorithm=ALGORITHM)


def verify_password_reset_token(token) -> user_db:
    """Verify a password reset token and mark it as used."""

    try:
        payload = jwt.decode(
            token,
            EMAIL_SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        if payload.get("type") != "password_reset":
            raise ValueError("Invalid token type.")

        reset_token = PasswordResetToken.objects.select_related("user").get(
            jti=payload["jti"]
        )

        if reset_token.used_at is not None:
            raise ValueError("This reset link has already been used.")

        if ensure_aware_datetime(reset_token.expires_at) <= timezone.now():
            raise ValueError("Reset link has expired.")

        reset_token.used_at = timezone.now()
        reset_token.save(update_fields=["used_at"])

        return payload

    except PasswordResetToken.DoesNotExist as err:
        raise ValueError("Invalid password reset token.") from err

    except jwt.ExpiredSignatureError as err:
        raise ValueError("Reset link has expired.") from err

    except jwt.InvalidTokenError as err:
        raise ValueError("Invalid password reset token.") from err
